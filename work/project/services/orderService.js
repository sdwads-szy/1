const db = require('../config/db');

/**
 * 生成订单号
 * @param {string} prefix - 前缀（ORD/SUB）
 * @returns {string} 唯一订单号
 */
function generateOrderNo(prefix) {
  const timestamp = Date.now().toString(36).toUpperCase();
  const random = Math.random().toString(36).substring(2, 8).toUpperCase();
  return `${prefix}${timestamp}${random}`;
}

/**
 * 乐观锁扣减库存（事务内，最多重试3次，指数退避）
 * 场景树 §3.5: 下单扣库存 — 乐观锁 CAS
 */
async function deductStock(conn, skuId, shopId, quantity) {
  for (let retry = 0; retry < 3; retry++) {
    const [rows] = await conn.execute(
      'SELECT stock, version FROM inventories WHERE sku_id = ? AND shop_id = ?',
      [skuId, shopId]
    );

    if (!rows.length) throw new Error('SKU_NOT_FOUND');

    const { stock, version } = rows[0];
    if (stock < quantity) throw new Error('INSUFFICIENT_STOCK');

    const [result] = await conn.execute(
      'UPDATE inventories SET stock = stock - ?, version = version + 1 WHERE sku_id = ? AND shop_id = ? AND version = ? AND stock >= ?',
      [quantity, skuId, shopId, version, quantity]
    );

    if (result.affectedRows > 0) return;

    // 指数退避: 100ms / 200ms / 400ms
    if (retry < 2) {
      await new Promise(r => setTimeout(r, Math.pow(2, retry) * 100));
    }
  }
  throw new Error('INSUFFICIENT_STOCK');
}

/**
 * 创建订单（消费者下单结算）
 * 场景树 S5: 下单结算 — 主订单+子订单+order_items+库存预占(单TX)
 *
 * @param {number} userId - 用户ID（来自token）
 * @param {number} addressId - 收货地址ID
 * @param {number[]} cartItemIds - 勾选的购物车项ID列表
 * @param {string} paymentMethod - 支付方式（wechat/alipay/unionpay）
 * @returns {{ orderId: number, orderNo: string, totalAmount: string, subOrders: Array, status: string }}
 */
async function createOrder(userId, addressId, cartItemIds, paymentMethod) {
  // 1. 参数校验
  if (!addressId) throw new Error('MISSING_ADDRESS');
  if (!cartItemIds || !cartItemIds.length) throw new Error('MISSING_CART_ITEMS');
  if (paymentMethod && !['wechat', 'alipay', 'unionpay'].includes(paymentMethod)) {
    throw new Error('INVALID_PAYMENT_METHOD');
  }

  // 2. 校验地址归属
  const addresses = await db.query(
    'SELECT id FROM user_addresses WHERE id = ? AND user_id = ?',
    [addressId, userId]
  );
  if (!addresses.length) throw new Error('INVALID_ADDRESS');

  // 3. 查询勾选的购物车项（带库存、店铺状态、SKU信息）
  const placeholders = cartItemIds.map(() => '?').join(',');
  const cartItems = await db.query(
    `SELECT ci.id as cart_item_id, ci.sku_id, ci.shop_id, ci.quantity,
            s.price, s.spec_name, s.spu_id, s.image as sku_image,
            sp.name as spu_name, sp.default_image,
            inv.stock, inv.version as inv_version,
            sh.status as shop_status, sh.name as shop_name
     FROM cart_items ci
     JOIN sku s ON ci.sku_id = s.id
     JOIN spu sp ON s.spu_id = sp.id
     JOIN inventories inv ON s.id = inv.sku_id AND ci.shop_id = inv.shop_id
     JOIN shops sh ON ci.shop_id = sh.id
     WHERE ci.id IN (${placeholders}) AND ci.user_id = ? AND ci.checked = 1`,
    [...cartItemIds, userId]
  );

  if (!cartItems.length) throw new Error('CART_ITEMS_NOT_FOUND');

  // 4. 按店铺分组并校验
  const shopGroups = new Map();
  for (const item of cartItems) {
    // 校验店铺状态
    if (item.shop_status !== 'open') {
      const err = new Error('SHOP_FROZEN');
      err.shopName = item.shop_name;
      throw err;
    }
    // 校验库存
    if (item.stock < item.quantity) {
      const err = new Error('INSUFFICIENT_STOCK');
      err.skuName = item.spu_name + (item.spec_name ? ' - ' + item.spec_name : '');
      err.availableStock = item.stock;
      throw err;
    }

    if (!shopGroups.has(item.shop_id)) {
      shopGroups.set(item.shop_id, {
        shopId: item.shop_id,
        shopName: item.shop_name,
        items: [],
        totalAmount: 0
      });
    }
    const group = shopGroups.get(item.shop_id);
    group.items.push(item);
    group.totalAmount += parseFloat(item.price) * item.quantity;
  }

  // 5. 事务：创建订单 + 子订单 + 订单明细 + 扣库存 + 清购物车
  const conn = await db.beginTransaction();
  try {
    let totalAmount = 0;
    const subOrderResults = [];

    // 5a. 先创建主订单
    const orderNo = generateOrderNo('ORD');
    const [orderResult] = await conn.execute(
      'INSERT INTO orders (order_no, user_id, total_amount, status) VALUES (?, ?, ?, ?)',
      [orderNo, userId, 0, 'pending']
    );
    const orderId = orderResult.insertId;

    // 5b. 逐店铺创建子订单
    for (const [, group] of shopGroups) {
      const subOrderNo = generateOrderNo('SUB');
      const [subResult] = await conn.execute(
        'INSERT INTO sub_orders (sub_order_no, order_id, shop_id, amount, status) VALUES (?, ?, ?, ?, ?)',
        [subOrderNo, orderId, group.shopId, group.totalAmount.toFixed(2), 'pending']
      );
      const subOrderId = subResult.insertId;
      totalAmount += group.totalAmount;

      // 5c. 创建订单明细 + 扣减库存
      const items = [];
      for (const item of group.items) {
        const lineTotal = parseFloat(item.price) * item.quantity;

        await conn.execute(
          'INSERT INTO order_items (sub_order_id, sku_id, quantity, price, snapshot) VALUES (?, ?, ?, ?, ?)',
          [
            subOrderId,
            item.sku_id,
            item.quantity,
            item.price,
            JSON.stringify({
              spu_name: item.spu_name,
              spec_name: item.spec_name,
              default_image: item.default_image,
              sku_image: item.sku_image,
              shop_name: item.shop_name
            })
          ]
        );

        // 乐观锁扣库存（事务内重试）
        await deductStock(conn, item.sku_id, item.shop_id, item.quantity);

        items.push({
          skuId: item.sku_id,
          spuName: item.spu_name,
          specName: item.spec_name,
          quantity: item.quantity,
          price: item.price,
          image: item.default_image || item.sku_image
        });
      }

      subOrderResults.push({
        id: subOrderId,
        subOrderNo,
        shopId: group.shopId,
        shopName: group.shopName,
        amount: group.totalAmount.toFixed(2),
        status: 'pending',
        items
      });
    }

    // 5d. 更新主订单总金额
    await conn.execute(
      'UPDATE orders SET total_amount = ? WHERE id = ?',
      [totalAmount.toFixed(2), orderId]
    );

    // 5e. 删除已下单的购物车项
    await conn.execute(
      `DELETE FROM cart_items WHERE id IN (${placeholders}) AND user_id = ?`,
      [...cartItemIds, userId]
    );

    // 6. 提交事务
    await db.commit(conn);

    return {
      orderId,
      orderNo,
      totalAmount: totalAmount.toFixed(2),
      subOrders: subOrderResults,
      status: 'pending'
    };
  } catch (e) {
    // 事务回滚 — 场景树: 下单失败→释放所有乐观锁预占库存（回滚自动释放）
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 获取用户订单列表
 * 支持状态筛选与分页
 *
 * @param {number} userId
 * @param {object} filters - { status, page, pageSize }
 * @returns {{ list: Array, total: number, page: number, pageSize: number }}
 */
async function getOrders(userId, filters = {}) {
  const { status, page = 1, pageSize = 20 } = filters;
  const offset = (page - 1) * pageSize;

  // 构建查询条件
  let whereClause = 'WHERE o.user_id = ?';
  const params = [userId];
  if (status) {
    whereClause += ' AND o.status = ?';
    params.push(status);
  }

  // 查询总数
  const countRows = await db.query(
    `SELECT COUNT(*) as total FROM orders o ${whereClause}`,
    params
  );
  const total = countRows[0].total;

  // 查询订单列表
  const orders = await db.query(
    `SELECT o.id, o.order_no, o.total_amount, o.status, o.paid_at, o.created_at, o.updated_at
     FROM orders o
     ${whereClause}
     ORDER BY o.created_at DESC
     LIMIT ? OFFSET ?`,
    [...params, pageSize, offset]
  );

  if (!orders.length) {
    return { list: [], total, page, pageSize };
  }

  // 批量查询子订单
  const orderIds = orders.map(o => o.id);
  const subPlaceholders = orderIds.map(() => '?').join(',');
  const subOrders = await db.query(
    `SELECT so.id, so.sub_order_no, so.order_id, so.shop_id, so.amount, so.status, sh.name as shop_name
     FROM sub_orders so
     JOIN shops sh ON so.shop_id = sh.id
     WHERE so.order_id IN (${subPlaceholders})
     ORDER BY so.id`,
    orderIds
  );

  // 组装数据
  const subOrdersMap = {};
  for (const so of subOrders) {
    if (!subOrdersMap[so.order_id]) subOrdersMap[so.order_id] = [];
    subOrdersMap[so.order_id].push({
      id: so.id,
      subOrderNo: so.sub_order_no,
      shopId: so.shop_id,
      shopName: so.shop_name,
      amount: so.amount,
      status: so.status
    });
  }

  const list = orders.map(o => ({
    id: o.id,
    orderNo: o.order_no,
    totalAmount: o.total_amount,
    status: o.status,
    paidAt: o.paid_at,
    subOrders: subOrdersMap[o.id] || [],
    createdAt: o.created_at,
    updatedAt: o.updated_at
  }));

  return { list, total, page, pageSize };
}

/**
 * 获取订单详情（含子订单、订单明细、支付信息、物流信息）
 *
 * @param {number} userId - 用户ID（用于归属校验）
 * @param {number} orderId - 订单ID
 * @returns {object} 完整订单详情
 */
async function getOrderDetail(userId, orderId) {
  // 查询主订单
  const orders = await db.query(
    'SELECT id, order_no, user_id, total_amount, status, paid_at, created_at, updated_at FROM orders WHERE id = ?',
    [orderId]
  );
  if (!orders.length) throw new Error('ORDER_NOT_FOUND');

  const order = orders[0];

  // 归属校验 — 消费者只能查看自己的订单
  if (order.user_id !== userId) throw new Error('ORDER_NOT_BELONG');

  // 查询子订单
  const subOrders = await db.query(
    `SELECT so.id, so.sub_order_no, so.shop_id, so.amount, so.status, sh.name as shop_name, sh.logo as shop_logo
     FROM sub_orders so
     JOIN shops sh ON so.shop_id = sh.id
     WHERE so.order_id = ?
     ORDER BY so.id`,
    [orderId]
  );

  const subOrderIds = subOrders.map(so => so.id);

  // 查询订单明细
  let orderItems = [];
  if (subOrderIds.length) {
    const itemPlaceholders = subOrderIds.map(() => '?').join(',');
    orderItems = await db.query(
      `SELECT oi.id, oi.sub_order_id, oi.sku_id, oi.quantity, oi.price, oi.snapshot
       FROM order_items oi
       WHERE oi.sub_order_id IN (${itemPlaceholders})
       ORDER BY oi.id`,
      subOrderIds
    );
  }

  // 查询支付记录
  let payments = [];
  if (subOrderIds.length) {
    const payPlaceholders = subOrderIds.map(() => '?').join(',');
    payments = await db.query(
      `SELECT p.id, p.transaction_no, p.sub_order_id, p.channel, p.amount, p.status
       FROM payments p
       WHERE p.sub_order_id IN (${payPlaceholders})`,
      subOrderIds
    );
  }

  // 查询物流记录
  let shipments = [];
  if (subOrderIds.length) {
    const shipPlaceholders = subOrderIds.map(() => '?').join(',');
    shipments = await db.query(
      `SELECT s.id, s.sub_order_id, s.tracking_no, s.carrier_code, s.status
       FROM shipments s
       WHERE s.sub_order_id IN (${shipPlaceholders})`,
      subOrderIds
    );
  }

  // 组装数据
  const itemsBySubOrder = {};
  for (const item of orderItems) {
    if (!itemsBySubOrder[item.sub_order_id]) itemsBySubOrder[item.sub_order_id] = [];
    let snapshot = {};
    try { snapshot = JSON.parse(item.snapshot || '{}'); } catch (e) { /* ignore */ }
    itemsBySubOrder[item.sub_order_id].push({
      id: item.id,
      skuId: item.sku_id,
      quantity: item.quantity,
      price: item.price,
      spuName: snapshot.spu_name || '',
      specName: snapshot.spec_name || '',
      image: snapshot.default_image || snapshot.sku_image || ''
    });
  }

  const paymentBySubOrder = {};
  for (const p of payments) {
    paymentBySubOrder[p.sub_order_id] = {
      id: p.id,
      transactionNo: p.transaction_no,
      channel: p.channel,
      amount: p.amount,
      status: p.status
    };
  }

  const shipmentBySubOrder = {};
  for (const s of shipments) {
    shipmentBySubOrder[s.sub_order_id] = {
      id: s.id,
      trackingNo: s.tracking_no,
      carrierCode: s.carrier_code,
      status: s.status
    };
  }

  const subOrderList = subOrders.map(so => ({
    id: so.id,
    subOrderNo: so.sub_order_no,
    shopId: so.shop_id,
    shopName: so.shop_name,
    shopLogo: so.shop_logo,
    amount: so.amount,
    status: so.status,
    items: itemsBySubOrder[so.id] || [],
    payment: paymentBySubOrder[so.id] || null,
    shipment: shipmentBySubOrder[so.id] || null
  }));

  return {
    id: order.id,
    orderNo: order.order_no,
    totalAmount: order.total_amount,
    status: order.status,
    paidAt: order.paid_at,
    subOrders: subOrderList,
    createdAt: order.created_at,
    updatedAt: order.updated_at
  };
}

/**
 * 确认收货
 * 场景树 S9: 确认收货 — order status→已完成
 *
 * @param {number} userId
 * @param {number} orderId
 * @returns {{ orderId: number, status: string }}
 */
async function confirmReceive(userId, orderId) {
  // 查询订单
  const orders = await db.query(
    'SELECT id, user_id, status FROM orders WHERE id = ?',
    [orderId]
  );
  if (!orders.length) throw new Error('ORDER_NOT_FOUND');

  const order = orders[0];

  // 归属校验
  if (order.user_id !== userId) throw new Error('ORDER_NOT_BELONG');

  // 状态校验 — 只有「已发货」状态可确认收货
  if (order.status !== 'shipped') throw new Error('INVALID_STATUS');

  // 事务：更新主订单 + 所有子订单状态
  const conn = await db.beginTransaction();
  try {
    await conn.execute(
      'UPDATE orders SET status = ? WHERE id = ? AND status = ?',
      ['completed', orderId, 'shipped']
    );

    await conn.execute(
      'UPDATE sub_orders SET status = ? WHERE order_id = ? AND status = ?',
      ['completed', orderId, 'shipped']
    );

    await db.commit(conn);

    return { orderId, status: 'completed' };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = {
  createOrder,
  getOrders,
  getOrderDetail,
  confirmReceive
};

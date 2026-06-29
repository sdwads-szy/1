const db = require('../config/db');
const { generate } = require('../utils/snowflake');

/**
 * 创建订单：校验库存→预扣库存→创建订单→创建支付单→清空购物车
 * @param {number} userId - 用户ID
 * @param {object} options - { addressId, cartItemIds, couponId, payChannel }
 * @returns {Promise<{orderId: number, orderNo: string, paymentId: number, payAmount: string}>}
 */
async function createOrder(userId, { addressId, cartItemIds, couponId, payChannel }) {
  // 1. 输入校验
  if (!cartItemIds || !Array.isArray(cartItemIds) || cartItemIds.length === 0) {
    throw new Error('CART_EMPTY');
  }
  if (!addressId) {
    throw new Error('ADDRESS_REQUIRED');
  }
  if (!payChannel || !['alipay', 'wxpay'].includes(payChannel)) {
    throw new Error('INVALID_PAY_CHANNEL');
  }

  // 2. 验证收货地址归属
  const addresses = await db.query(
    'SELECT id FROM addresses WHERE id = ? AND user_id = ?',
    [addressId, userId]
  );
  if (!addresses.length) {
    throw new Error('ADDRESS_REQUIRED');
  }

  // 3. 获取购物车商品（含 SKU 和商品信息）
  const cartItems = await db.query(
    `SELECT c.id AS cart_id, c.sku_id, c.quantity,
            s.product_id, s.price, s.stock, s.spec_combo, s.image,
            p.title AS product_title, p.shop_id, p.status AS product_status
     FROM carts c
     JOIN skus s ON c.sku_id = s.id
     JOIN products p ON s.product_id = p.id
     WHERE c.id IN (?) AND c.user_id = ?`,
    [cartItemIds, userId]
  );

  if (!cartItems.length) {
    throw new Error('CART_EMPTY');
  }

  // 检查商品是否在售
  for (const item of cartItems) {
    if (item.product_status !== 'approved' && item.product_status !== 'listed') {
      throw new Error('PRODUCT_UNAVAILABLE');
    }
  }

  // 4. 按店铺分组（分拆结算）
  const shopGroups = new Map();
  for (const item of cartItems) {
    if (!shopGroups.has(item.shop_id)) {
      shopGroups.set(item.shop_id, []);
    }
    shopGroups.get(item.shop_id).push(item);
  }

  // 5. 校验优惠券（如果有）
  let couponInfo = null;
  if (couponId) {
    const coupons = await db.query(
      `SELECT c.* FROM coupons c WHERE c.id = ? AND c.status = 'active'
       AND c.valid_from <= NOW() AND c.valid_to >= NOW()`,
      [couponId]
    );
    if (!coupons.length) {
      throw new Error('COUPON_INVALID');
    }

    const userCoupons = await db.query(
      `SELECT * FROM user_coupons
       WHERE user_id = ? AND coupon_id = ? AND status = 'available'`,
      [userId, couponId]
    );
    if (!userCoupons.length) {
      throw new Error('COUPON_INVALID');
    }

    couponInfo = { coupon: coupons[0], userCoupon: userCoupons[0] };
  }

  // 6. 开启事务
  const conn = await db.beginTransaction();
  try {
    const results = [];
    let couponApplied = false;

    for (const [shopId, items] of shopGroups) {
      const shopIdNum = parseInt(shopId);

      // 6a. 锁定 SKU 库存行（FOR UPDATE 防超卖）
      const skuIds = items.map(i => i.sku_id);
      const [lockedRows] = await conn.execute(
        'SELECT id, stock, price FROM skus WHERE id IN (?) FOR UPDATE',
        [skuIds]
      );

      const skuMap = {};
      for (const row of lockedRows) {
        skuMap[row.id] = { stock: row.stock, price: row.price };
      }

      // 6b. 校验库存
      for (const item of items) {
        const sku = skuMap[item.sku_id];
        if (!sku || sku.stock < item.quantity) {
          throw new Error('INSUFFICIENT_STOCK');
        }
      }

      // 6c. 计算金额
      let totalAmount = 0;
      for (const item of items) {
        totalAmount += parseFloat(item.price) * item.quantity;
      }

      let discountAmount = 0;

      // 6d. 应用优惠券（仅第一个符合条件的店铺组）
      if (couponInfo && !couponApplied) {
        const minOrder = parseFloat(couponInfo.coupon.min_order);
        if (totalAmount >= minOrder) {
          discountAmount = Math.min(parseFloat(couponInfo.coupon.amount), totalAmount);
          discountAmount = Math.round(discountAmount * 100) / 100;

          // 标记优惠券为已使用
          await conn.execute(
            'UPDATE user_coupons SET status = ?, used_at = NOW() WHERE id = ? AND status = ?',
            ['used', couponInfo.userCoupon.id, 'available']
          );
          couponApplied = true;
        }
      }

      const payAmount = Math.round((totalAmount - discountAmount) * 100) / 100;

      // 6e. 扣减库存（乐观锁条件：stock >= quantity）
      for (const item of items) {
        const [deductResult] = await conn.execute(
          'UPDATE skus SET stock = stock - ? WHERE id = ? AND stock >= ?',
          [item.quantity, item.sku_id, item.quantity]
        );
        if (!deductResult.affectedRows) {
          throw new Error('INSUFFICIENT_STOCK');
        }
      }

      // 6f. 生成订单号并创建订单
      const orderNo = generate();
      const [orderResult] = await conn.execute(
        `INSERT INTO orders (order_no, user_id, shop_id, total_amount, discount_amount, pay_amount, status, pay_method)
         VALUES (?, ?, ?, ?, ?, ?, 'pending_pay', ?)`,
        [orderNo, userId, shopIdNum, totalAmount.toFixed(2), discountAmount.toFixed(2), payAmount.toFixed(2), payChannel]
      );
      const orderId = orderResult.insertId;

      // 标记 user_coupons 的 order_id
      if (couponApplied && couponInfo) {
        await conn.execute(
          'UPDATE user_coupons SET order_id = ? WHERE id = ?',
          [orderId, couponInfo.userCoupon.id]
        );
      }

      // 6g. 创建订单商品快照
      for (const item of items) {
        const snapshot = JSON.stringify({
          sku_id: item.sku_id,
          spec_combo: item.spec_combo,
          price: String(item.price),
          image: item.image,
          product_title: item.product_title
        });
        await conn.execute(
          'INSERT INTO order_items (order_id, sku_id, sku_snapshot, quantity, unit_price) VALUES (?, ?, ?, ?, ?)',
          [orderId, item.sku_id, snapshot, item.quantity, item.price]
        );
      }

      // 6h. 创建支付单
      const [paymentResult] = await conn.execute(
        `INSERT INTO payments (order_id, user_id, amount, channel, status)
         VALUES (?, ?, ?, ?, 'pending')`,
        [orderId, userId, payAmount.toFixed(2), payChannel]
      );

      results.push({
        orderId,
        orderNo,
        paymentId: paymentResult.insertId,
        payAmount: payAmount.toFixed(2)
      });
    }

    // 7. 清空已购购物车项
    await conn.execute(
      'DELETE FROM carts WHERE id IN (?) AND user_id = ?',
      [cartItemIds, userId]
    );

    // 8. 提交事务
    await db.commit(conn);

    return results[0];
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 获取用户订单列表
 * @param {number} userId
 * @param {object} options - { status, page, pageSize }
 * @returns {Promise<{list: Array, total: number, page: number, pageSize: number}>}
 */
async function getOrderList(userId, { status, page: rawPage, pageSize: rawPageSize }) {
  const page = parseInt(rawPage) || 1;
  const pageSize = parseInt(rawPageSize) || 20;

  let whereClause = 'WHERE o.user_id = ?';
  const params = [userId];

  if (status) {
    whereClause += ' AND o.status = ?';
    params.push(status);
  }

  // 总数
  const countResult = await db.query(
    `SELECT COUNT(*) AS total FROM orders o ${whereClause}`,
    params
  );
  const total = countResult[0].total;

  // 列表（含店铺名和商品数量）
  const list = await db.query(
    `SELECT o.id, o.order_no AS orderNo, o.status, o.pay_amount AS payAmount,
            o.shop_id AS shopId, s.name AS shopName, o.created_at AS createdAt,
            (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) AS itemCount
     FROM orders o
     LEFT JOIN shops s ON o.shop_id = s.id
     ${whereClause}
     ORDER BY o.created_at DESC
     LIMIT ? OFFSET ?`,
    [...params, pageSize, (page - 1) * pageSize]
  );

  // DECIMAL → 字符串
  const formattedList = list.map(item => ({
    ...item,
    payAmount: item.payAmount !== null ? String(item.payAmount) : '0.00'
  }));

  return { list: formattedList, total, page, pageSize };
}

/**
 * 获取订单详情（用户端）
 * @param {number} orderId
 * @param {number} userId - 用于所有权校验
 * @returns {Promise<object>}
 */
async function getOrderDetail(orderId, userId) {
  const orders = await db.query(
    `SELECT o.*, s.name AS shop_name
     FROM orders o
     LEFT JOIN shops s ON o.shop_id = s.id
     WHERE o.id = ? AND o.user_id = ?`,
    [orderId, userId]
  );
  if (!orders.length) {
    throw new Error('NOT_FOUND');
  }

  return buildOrderDetail(orders[0]);
}

/**
 * 构建订单详情（含商品/支付/时间线）
 * @param {object} order
 * @returns {Promise<object>}
 */
async function buildOrderDetail(order) {
  const orderId = order.id;

  // 订单商品
  const items = await db.query(
    'SELECT * FROM order_items WHERE order_id = ?',
    [orderId]
  );

  // 支付记录
  const payments = await db.query(
    'SELECT * FROM payments WHERE order_id = ?',
    [orderId]
  );

  // 构建时间线
  const timeline = [];
  if (order.created_at) {
    timeline.push({ status: 'pending_pay', time: order.created_at, label: '订单创建' });
  }
  if (order.pay_time) {
    timeline.push({ status: 'paid', time: order.pay_time, label: '已支付' });
  }
  if (order.ship_time) {
    timeline.push({ status: 'shipped', time: order.ship_time, label: '已发货' });
  }
  if (order.receive_time) {
    timeline.push({ status: 'received', time: order.receive_time, label: '已收货' });
  }
  if (order.status === 'cancelled') {
    timeline.push({ status: 'cancelled', time: order.updated_at, label: '已取消' });
  }
  if (order.status === 'completed') {
    timeline.push({ status: 'completed', time: order.updated_at, label: '已完成' });
  }

  return {
    id: order.id,
    orderNo: order.order_no,
    status: order.status,
    totalAmount: order.total_amount !== null ? String(order.total_amount) : '0.00',
    discountAmount: order.discount_amount !== null ? String(order.discount_amount) : '0.00',
    payAmount: order.pay_amount !== null ? String(order.pay_amount) : '0.00',
    payMethod: order.pay_method,
    payTime: order.pay_time,
    shipTime: order.ship_time,
    receiveTime: order.receive_time,
    shopName: order.shop_name,
    createdAt: order.created_at,
    items: items.map(i => ({
      id: i.id,
      skuId: i.sku_id,
      skuSnapshot: typeof i.sku_snapshot === 'string' ? JSON.parse(i.sku_snapshot) : i.sku_snapshot,
      quantity: i.quantity,
      unitPrice: String(i.unit_price)
    })),
    payment: payments[0] ? {
      id: payments[0].id,
      amount: String(payments[0].amount),
      channel: payments[0].channel,
      tradeNo: payments[0].trade_no,
      status: payments[0].status,
      paidAt: payments[0].paid_at,
      refundAmount: String(payments[0].refund_amount)
    } : null,
    timeline
  };
}

/**
 * 取消订单：释放库存→更新订单状态→关闭支付单
 * @param {number} orderId
 * @param {number} userId
 * @returns {Promise<{success: boolean}>}
 */
async function cancelOrder(orderId, userId) {
  // 校验归属和状态
  const orders = await db.query(
    'SELECT * FROM orders WHERE id = ? AND user_id = ?',
    [orderId, userId]
  );
  if (!orders.length) {
    throw new Error('NOT_FOUND');
  }
  if (orders[0].status !== 'pending_pay') {
    throw new Error('ORDER_CANNOT_CANCEL');
  }

  const conn = await db.beginTransaction();
  try {
    // 释放库存
    const [items] = await conn.execute(
      'SELECT sku_id, quantity FROM order_items WHERE order_id = ?',
      [orderId]
    );
    for (const item of items) {
      await conn.execute(
        'UPDATE skus SET stock = stock + ? WHERE id = ?',
        [item.quantity, item.sku_id]
      );
    }

    // 更新订单状态
    await conn.execute(
      "UPDATE orders SET status = 'cancelled', updated_at = NOW() WHERE id = ? AND status = 'pending_pay'",
      [orderId]
    );

    // 关闭支付单
    await conn.execute(
      "UPDATE payments SET status = 'closed', updated_at = NOW() WHERE order_id = ? AND status = 'pending'",
      [orderId]
    );

    // 如果使用了优惠券，恢复
    await conn.execute(
      "UPDATE user_coupons SET status = 'available', used_at = NULL, order_id = NULL WHERE order_id = ? AND status = 'used'",
      [orderId]
    );

    await db.commit(conn);
    return { success: true };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 确认收货：shipped → completed
 * @param {number} orderId
 * @param {number} userId
 * @returns {Promise<{success: boolean}>}
 */
async function confirmReceipt(orderId, userId) {
  const orders = await db.query(
    'SELECT * FROM orders WHERE id = ? AND user_id = ?',
    [orderId, userId]
  );
  if (!orders.length) {
    throw new Error('NOT_FOUND');
  }
  if (orders[0].status !== 'shipped') {
    throw new Error('ORDER_NOT_SHIPPED');
  }

  const result = await db.query(
    "UPDATE orders SET status = 'completed', receive_time = NOW(), updated_at = NOW() WHERE id = ? AND status = 'shipped'",
    [orderId]
  );

  if (!result.affectedRows) {
    throw new Error('ORDER_NOT_SHIPPED');
  }

  return { success: true };
}

/**
 * 商家发货：paid → shipped
 * @param {number} orderId
 * @param {number} userId - 商家用户ID，用于查找所属店铺
 * @returns {Promise<{success: boolean}>}
 */
async function shipOrder(orderId, userId) {
  // 查找商家店铺
  const shops = await db.query(
    "SELECT id FROM shops WHERE user_id = ? AND status = 'active'",
    [userId]
  );
  if (!shops.length) {
    throw new Error('NOT_MERCHANT');
  }
  const shopId = shops[0].id;

  // 校验订单归属和状态
  const orders = await db.query(
    'SELECT * FROM orders WHERE id = ?',
    [orderId]
  );
  if (!orders.length) {
    throw new Error('NOT_FOUND');
  }
  if (orders[0].shop_id !== shopId) {
    throw new Error('NOT_ORDER_OWNER');
  }
  if (orders[0].status !== 'paid') {
    throw new Error('ORDER_NOT_PAID');
  }

  const result = await db.query(
    "UPDATE orders SET status = 'shipped', ship_time = NOW(), updated_at = NOW() WHERE id = ? AND status = 'paid'",
    [orderId]
  );

  if (!result.affectedRows) {
    throw new Error('ORDER_NOT_PAID');
  }

  return { success: true };
}

// ===================== 管理端 =====================

/**
 * 管理端订单列表（多条件筛选）
 * @param {object} options - { orderNo, status, shopId, startDate, endDate, page, pageSize }
 * @returns {Promise<{list: Array, total: number, page: number, pageSize: number}>}
 */
async function adminGetOrderList({ orderNo, status, shopId, startDate, endDate, page: rawPage, pageSize: rawPageSize }) {
  const page = parseInt(rawPage) || 1;
  const pageSize = parseInt(rawPageSize) || 20;

  const whereClauses = [];
  const params = [];

  if (orderNo) {
    whereClauses.push('o.order_no LIKE ?');
    params.push(`%${orderNo}%`);
  }
  if (status) {
    whereClauses.push('o.status = ?');
    params.push(status);
  }
  if (shopId) {
    whereClauses.push('o.shop_id = ?');
    params.push(parseInt(shopId));
  }
  if (startDate) {
    whereClauses.push('o.created_at >= ?');
    params.push(startDate);
  }
  if (endDate) {
    whereClauses.push('o.created_at <= ?');
    params.push(endDate);
  }

  const whereSQL = whereClauses.length ? 'WHERE ' + whereClauses.join(' AND ') : '';

  // 总数
  const countResult = await db.query(
    `SELECT COUNT(*) AS total FROM orders o ${whereSQL}`,
    params
  );
  const total = countResult[0].total;

  // 列表
  const list = await db.query(
    `SELECT o.*, s.name AS shop_name, u.nickname AS user_nickname
     FROM orders o
     LEFT JOIN shops s ON o.shop_id = s.id
     LEFT JOIN users u ON o.user_id = u.id
     ${whereSQL}
     ORDER BY o.created_at DESC
     LIMIT ? OFFSET ?`,
    [...params, pageSize, (page - 1) * pageSize]
  );

  const formattedList = list.map(o => ({
    id: o.id,
    orderNo: o.order_no,
    userId: o.user_id,
    shopId: o.shop_id,
    totalAmount: o.total_amount !== null ? String(o.total_amount) : '0.00',
    discountAmount: o.discount_amount !== null ? String(o.discount_amount) : '0.00',
    payAmount: o.pay_amount !== null ? String(o.pay_amount) : '0.00',
    status: o.status,
    payMethod: o.pay_method,
    payTime: o.pay_time,
    shipTime: o.ship_time,
    receiveTime: o.receive_time,
    shopName: o.shop_name,
    userNickname: o.user_nickname,
    createdAt: o.created_at
  }));

  return { list: formattedList, total, page, pageSize };
}

/**
 * 管理端订单详情（含退款信息）
 * @param {number} orderId
 * @returns {Promise<object>}
 */
async function adminGetOrderDetail(orderId) {
  const orders = await db.query(
    `SELECT o.*, s.name AS shop_name, u.nickname AS user_nickname, u.phone AS user_phone
     FROM orders o
     LEFT JOIN shops s ON o.shop_id = s.id
     LEFT JOIN users u ON o.user_id = u.id
     WHERE o.id = ?`,
    [orderId]
  );
  if (!orders.length) {
    throw new Error('NOT_FOUND');
  }

  const order = orders[0];
  const detail = await buildOrderDetail(order);

  // 退款记录
  const refunds = await db.query(
    'SELECT * FROM refunds WHERE order_id = ?',
    [orderId]
  );

  return {
    order: {
      ...detail,
      userId: order.user_id,
      shopId: order.shop_id,
      userNickname: order.user_nickname,
      userPhone: order.user_phone,
      updatedAt: order.updated_at
    },
    items: detail.items,
    payment: detail.payment,
    refund: refunds[0] || null,
    timeline: detail.timeline
  };
}

module.exports = {
  createOrder,
  getOrderList,
  getOrderDetail,
  cancelOrder,
  confirmReceipt,
  shipOrder,
  adminGetOrderList,
  adminGetOrderDetail
};

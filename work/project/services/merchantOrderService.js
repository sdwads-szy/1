const db = require('../config/db');

/**
 * 根据 merchant userId 获取 shopId
 * @param {number} userId - 用户ID（从 token 中获取）
 * @returns {Promise<number>} shopId
 */
async function getShopIdByUserId(userId) {
  const merchants = await db.query(
    'SELECT id FROM merchants WHERE user_id = ? AND status = ?',
    [userId, 'approved']
  );
  if (!merchants.length) {
    throw new Error('NOT_MERCHANT');
  }

  const shops = await db.query(
    'SELECT id FROM shops WHERE merchant_id = ? AND status != ?',
    [merchants[0].id, 'frozen']
  );
  if (!shops.length) {
    throw new Error('NO_SHOP');
  }

  return shops[0].id;
}

/**
 * 商家订单列表查询
 * @param {number} userId - 商家用户ID
 * @param {{ page: number, pageSize: number, status: string|null }} filters
 * @returns {Promise<{ list: Array, total: number, page: number, pageSize: number }>}
 */
async function getOrderList(userId, { page, pageSize, status }) {
  const shopId = await getShopIdByUserId(userId);

  // 构建查询条件
  const conditions = ['so.shop_id = ?'];
  const params = [shopId];

  if (status) {
    conditions.push('so.status = ?');
    params.push(status);
  }

  const whereClause = conditions.length ? 'WHERE ' + conditions.join(' AND ') : '';

  // 查询总数
  const countSql = `SELECT COUNT(*) as total FROM sub_orders so ${whereClause}`;
  const countRows = await db.query(countSql, params);
  const total = countRows[0].total;

  // 分页查询子订单
  const offset = (page - 1) * pageSize;
  const listSql = `SELECT so.id, so.sub_order_no, so.order_id, so.shop_id, so.amount, so.status, so.created_at, so.updated_at, o.order_no, o.user_id, o.total_amount, o.status AS order_status FROM sub_orders so JOIN orders o ON so.order_id = o.id ${whereClause} ORDER BY so.created_at DESC LIMIT ? OFFSET ?`;
  const subOrders = await db.query(listSql, [...params, pageSize, offset]);

  // 批量查询订单明细
  const subOrderIds = subOrders.map(so => so.id);
  const allItems = subOrderIds.length > 0
    ? await db.query(
        `SELECT id, sub_order_id, sku_id, quantity, price, snapshot FROM order_items WHERE sub_order_id IN (${subOrderIds.map(() => '?').join(',')})`,
        subOrderIds
      )
    : [];

  // 按 sub_order_id 分组
  const itemsMap = {};
  allItems.forEach(function(item) {
    if (!itemsMap[item.sub_order_id]) {
      itemsMap[item.sub_order_id] = [];
    }
    itemsMap[item.sub_order_id].push(item);
  });

  // 组装结果
  const list = subOrders.map(so => ({
    id: so.id,
    sub_order_no: so.sub_order_no,
    order_id: so.order_id,
    order_no: so.order_no,
    shop_id: so.shop_id,
    amount: so.amount,
    status: so.status,
    user_id: so.user_id,
    total_amount: so.total_amount,
    order_status: so.order_status,
    items: itemsMap[so.id] || [],
    created_at: so.created_at,
    updated_at: so.updated_at,
  }));

  return { list, total, page, pageSize };
}

/**
 * 商家发货 — 为已付款的子订单录入物流信息
 * @param {number} userId - 商家用户ID
 * @param {number} subOrderId - 子订单ID
 * @param {string} trackingNo - 物流单号
 * @param {string} carrierCode - 快递公司代码
 * @returns {Promise<{ id: number, tracking_no: string, carrier_code: string, status: string }>}
 */
async function shipOrder(userId, subOrderId, trackingNo, carrierCode) {
  const shopId = await getShopIdByUserId(userId);

  const conn = await db.beginTransaction();
  try {
    const [subOrderRows] = await conn.execute(
      `SELECT id, sub_order_no, order_id, shop_id, status
       FROM sub_orders
       WHERE id = ? AND shop_id = ?
       FOR UPDATE`,
      [subOrderId, shopId]
    );

    if (!subOrderRows || !subOrderRows.length) {
      await db.rollback(conn);
      throw new Error('SUB_ORDER_NOT_FOUND');
    }

    const subOrder = subOrderRows[0];

    if (subOrder.shop_id !== shopId) {
      await db.rollback(conn);
      throw new Error('NOT_BELONG_TO_SHOP');
    }

    if (subOrder.status !== 'paid') {
      await db.rollback(conn);
      throw new Error('ORDER_STATUS');
    }

    const [existingShipments] = await conn.execute(
      'SELECT id FROM shipments WHERE sub_order_id = ?',
      [subOrderId]
    );
    if (existingShipments && existingShipments.length > 0) {
      await db.rollback(conn);
      throw new Error('SHIPMENT_EXISTS');
    }

    const [insertResult] = await conn.execute(
      `INSERT INTO shipments (sub_order_id, tracking_no, carrier_code, status)
       VALUES (?, ?, ?, 'pending_pickup')`,
      [subOrderId, trackingNo, carrierCode]
    );

    const [updateResult] = await conn.execute(
      `UPDATE sub_orders SET status = 'shipped'
       WHERE id = ? AND status = 'paid'`,
      [subOrderId]
    );

    if (updateResult.affectedRows === 0) {
      await db.rollback(conn);
      throw new Error('CONCURRENCY_CONFLICT');
    }

    await conn.execute(
      `UPDATE orders SET status = 'shipped'
       WHERE id = ?
         AND status = 'paid'
         AND NOT EXISTS (
           SELECT 1 FROM sub_orders
           WHERE order_id = orders.id AND status = 'paid'
         )`,
      [subOrder.order_id]
    );

    await db.commit(conn);

    return {
      id: insertResult.insertId,
      sub_order_id: subOrderId,
      tracking_no: trackingNo,
      carrier_code: carrierCode,
      status: 'pending_pickup',
    };
  } catch (err) {
    await db.rollback(conn);
    throw err;
  }
}

module.exports = { getOrderList, shipOrder };

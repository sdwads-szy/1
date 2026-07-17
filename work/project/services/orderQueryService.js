const db = require('../config/db');

/**
 * 按用户ID查询订单列表（分页+状态筛选）
 * @param {number} userId — 买家用户ID
 * @param {object} options — { status, page, pageSize }
 * @returns {{ list, total, page, pageSize }}
 */
async function getOrdersByUser(userId, options) {
  const { status, page, pageSize } = Object.assign({ page: 1, pageSize: 20 }, options);
  const params = [userId];
  let whereClause = 'WHERE user_id = ?';

  if (status) {
    whereClause += ' AND status = ?';
    params.push(status);
  }

  const countSql = 'SELECT COUNT(*) as total FROM orders ' + whereClause;
  const countResult = await db.query(countSql, params);
  const total = countResult[0].total;

  const offset = (page - 1) * pageSize;
  const dataSql = 'SELECT id, order_no, total_amount, status, paid_at, created_at FROM orders ' +
    whereClause + ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
  const rows = await db.query(dataSql, [...params, pageSize, offset]);

  return { list: rows, total, page, pageSize };
}

/**
 * 按主键查询订单
 * @param {number} id — 订单ID
 * @returns {object} — 订单行，含 user_id 用于所有权校验
 * @throws ORDER_NOT_FOUND
 */
async function getOrderById(id) {
  const sql = 'SELECT id, order_no, user_id, total_amount, status, paid_at, created_at, updated_at FROM orders WHERE id = ?';
  const rows = await db.query(sql, [id]);
  if (!rows.length) {
    throw new Error('ORDER_NOT_FOUND');
  }
  return rows[0];
}

/**
 * 按主订单ID查询所有子订单（JOIN shops 获取店铺名）
 * @param {number} orderId — 主订单ID
 * @returns {array} — 子订单列表
 */
async function getSubOrdersByOrder(orderId) {
  const sql = 'SELECT so.id, so.sub_order_no, so.order_id, so.shop_id, so.amount, so.status, so.created_at, s.name AS shop_name FROM sub_orders so LEFT JOIN shops s ON so.shop_id = s.id WHERE so.order_id = ? ORDER BY so.id';
  return await db.query(sql, [orderId]);
}

/**
 * 按店铺ID查询子订单（商家后台用，分页+状态筛选）
 * @param {number} shopId — 店铺ID
 * @param {object} options — { status, page, pageSize }
 * @returns {{ list, total, page, pageSize }}
 */
async function getSubOrdersByShop(shopId, options) {
  const { status, page, pageSize } = Object.assign({ page: 1, pageSize: 20 }, options);
  const params = [shopId];
  let whereClause = 'WHERE shop_id = ?';

  if (status) {
    whereClause += ' AND status = ?';
    params.push(status);
  }

  const countSql = 'SELECT COUNT(*) as total FROM sub_orders ' + whereClause;
  const countResult = await db.query(countSql, params);
  const total = countResult[0].total;

  const offset = (page - 1) * pageSize;
  const dataSql = 'SELECT id, sub_order_no, order_id, shop_id, amount, status, created_at FROM sub_orders ' +
    whereClause + ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
  const rows = await db.query(dataSql, [...params, pageSize, offset]);

  return { list: rows, total, page, pageSize };
}

/**
 * 按子订单ID查询订单明细
 * @param {number} subOrderId — 子订单ID
 * @returns {array} — 明细列表
 */
async function getOrderItems(subOrderId) {
  const sql = 'SELECT id, sku_id, quantity, price, snapshot FROM order_items WHERE sub_order_id = ?';
  return await db.query(sql, [subOrderId]);
}

/**
 * 确认收货：将订单及子订单状态从 shipped 变更为 completed
 * @param {number} orderId — 订单ID
 * @param {number} userId — 买家用户ID
 * @returns {{ orderId, status }}
 * @throws ORDER_NOT_FOUND | NOT_OWN_ORDER | ORDER_STATUS_INVALID
 */
async function confirmReceive(orderId, userId) {
  const order = await getOrderById(orderId);
  if (order.user_id !== userId) {
    throw new Error('NOT_OWN_ORDER');
  }
  if (order.status !== 'shipped') {
    throw new Error('ORDER_STATUS_INVALID');
  }

  const conn = await db.beginTransaction();
  try {
    const updateOrderSql = "UPDATE orders SET status = 'completed' WHERE id = ? AND status = 'shipped'";
    const [result] = await conn.execute(updateOrderSql, [orderId]);
    if (result.affectedRows === 0) {
      throw new Error('ORDER_STATUS_INVALID');
    }

    const updateSubSql = "UPDATE sub_orders SET status = 'completed' WHERE order_id = ? AND status = 'shipped'";
    await conn.execute(updateSubSql, [orderId]);

    await db.commit(conn);
    return { orderId, status: 'completed' };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = {
  getOrdersByUser,
  getOrderById,
  getSubOrdersByOrder,
  getSubOrdersByShop,
  getOrderItems,
  confirmReceive,
};

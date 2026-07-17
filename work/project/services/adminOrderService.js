const db = require('../config/db');

/**
 * 平台全局订单查询 — 支持 orderNo/status/shopId 组合筛选 + 分页
 * @param {Object} filters
 * @param {string} [filters.orderNo]  - 订单号精确搜索
 * @param {string} [filters.status]   - 订单状态筛选
 * @param {number} [filters.shopId]   - 店铺ID筛选（JOIN sub_orders）
 * @param {number} filters.page       - 页码，默认1
 * @param {number} filters.pageSize   - 每页条数，默认20
 * @returns {Promise<{list: Array, total: number, page: number, pageSize: number}>}
 */
async function getAdminOrders(filters) {
  const { orderNo, status, shopId, page, pageSize } = filters;

  const conditions = [];
  const params = [];

  // 基础 FROM 子句：shopId 存在时 JOIN sub_orders
  let baseFrom = 'FROM orders o';

  if (shopId) {
    baseFrom += ' INNER JOIN sub_orders so ON so.order_id = o.id';
    conditions.push('so.shop_id = ?');
    params.push(shopId);
  }

  if (orderNo) {
    conditions.push('o.order_no = ?');
    params.push(orderNo);
  }

  if (status) {
    conditions.push('o.status = ?');
    params.push(status);
  }

  const whereClause = conditions.length > 0
    ? 'WHERE ' + conditions.join(' AND ')
    : '';

  // 计数查询
  const countCol = shopId ? 'COUNT(DISTINCT o.id)' : 'COUNT(*)';
  const countSql = `SELECT ${countCol} as total ${baseFrom} ${whereClause}`;
  const countRows = await db.query(countSql, params);
  const total = countRows[0].total;

  // 列表查询
  const offset = (page - 1) * pageSize;
  const listSql = `SELECT o.id, o.order_no, o.user_id, o.total_amount, o.status, o.paid_at, o.created_at ${baseFrom} ${whereClause} ORDER BY o.created_at DESC LIMIT ? OFFSET ?`;
  const listParams = [...params, pageSize, offset];
  const list = await db.query(listSql, listParams);

  return { list, total, page, pageSize };
}

module.exports = { getAdminOrders };

const db = require('../config/db');

/**
 * 获取商家售后申请列表
 * @param {number} userId - 当前登录用户ID（req.userId）
 * @param {number} page - 页码
 * @param {number} pageSize - 每页条数
 * @param {object} filters - 筛选条件 { status, type, requestNo }
 * @returns {{ list: array, total: number, page: number, pageSize: number }}
 */
async function getMerchantRefundList(userId, page, pageSize, filters) {
  // 确认用户是商家
  const merchantRows = await db.query(
    'SELECT id FROM merchants WHERE user_id = ?',
    [userId]
  );
  if (!merchantRows.length) throw new Error('NOT_MERCHANT');
  const merchantId = merchantRows[0].id;

  // 构建查询条件
  const conditions = ['m.id = ?'];
  const params = [merchantId];

  if (filters.status) {
    conditions.push('rr.status = ?');
    params.push(filters.status);
  }
  if (filters.type) {
    conditions.push('rr.type = ?');
    params.push(filters.type);
  }
  if (filters.requestNo) {
    conditions.push('rr.request_no LIKE ?');
    params.push('%' + filters.requestNo + '%');
  }

  const whereClause = conditions.join(' AND ');

  // 统计总数
  const countSql =
    'SELECT COUNT(*) as total ' +
    'FROM refund_requests rr ' +
    'JOIN sub_orders so ON rr.sub_order_id = so.id ' +
    'JOIN shops s ON so.shop_id = s.id ' +
    'JOIN merchants m ON s.merchant_id = m.id ' +
    'WHERE ' + whereClause;
  const countResult = await db.query(countSql, params);
  const total = countResult[0].total;

  // 分页查询列表
  const offset = (page - 1) * pageSize;
  const listSql =
    'SELECT ' +
    'rr.id, rr.request_no, rr.sub_order_id, rr.user_id, ' +
    'rr.type, rr.reason, rr.amount, rr.evidence_images, ' +
    'rr.status, rr.merchant_review_reason, rr.arbitration_ruling, ' +
    'rr.created_at, rr.updated_at, ' +
    'so.sub_order_no, so.amount AS sub_order_amount, ' +
    'o.order_no, u.nickname AS user_nickname, u.mobile AS user_mobile ' +
    'FROM refund_requests rr ' +
    'JOIN sub_orders so ON rr.sub_order_id = so.id ' +
    'JOIN orders o ON so.order_id = o.id ' +
    'JOIN shops s ON so.shop_id = s.id ' +
    'JOIN merchants m ON s.merchant_id = m.id ' +
    'JOIN users u ON rr.user_id = u.id ' +
    'WHERE ' + whereClause + ' ' +
    'ORDER BY rr.created_at DESC ' +
    'LIMIT ? OFFSET ?';
  const list = await db.query(listSql, [...params, pageSize, offset]);

  return { list, total, page, pageSize };
}

/**
 * 商家审批售后申请（同意/拒绝）
 * @param {number} userId - 当前登录用户ID（req.userId）
 * @param {number} refundRequestId - 售后申请ID
 * @param {string} action - 'approve' | 'reject'
 * @param {string|null} reason - 拒绝原因（拒绝时必填）
 * @returns {object} 更新后的售后单
 */
async function approveRefund(userId, refundRequestId, action, reason) {
  // 确认用户是商家
  const merchantRows = await db.query(
    'SELECT id FROM merchants WHERE user_id = ?',
    [userId]
  );
  if (!merchantRows.length) throw new Error('NOT_MERCHANT');
  const merchantId = merchantRows[0].id;

  // 查询售后单，验证归属
  const refundSql =
    'SELECT rr.*, so.id AS so_id, so.shop_id, so.amount AS sub_order_amount, ' +
    's.merchant_id AS shop_merchant_id ' +
    'FROM refund_requests rr ' +
    'JOIN sub_orders so ON rr.sub_order_id = so.id ' +
    'JOIN shops s ON so.shop_id = s.id ' +
    'WHERE rr.id = ?';
  const refundRows = await db.query(refundSql, [refundRequestId]);
  if (!refundRows.length) throw new Error('NOT_FOUND');

  const refund = refundRows[0];

  // 验证售后单属于当前商家
  if (refund.shop_merchant_id !== merchantId) {
    throw new Error('NOT_YOUR_SHOP');
  }

  // 验证售后单状态为待审核
  if (refund.status !== 'pending') {
    throw new Error('INVALID_STATUS');
  }

  // 验证退款金额不超过子订单实付金额
  if (action === 'approve' && Number(refund.amount) > Number(refund.sub_order_amount)) {
    throw new Error('EXCEED_AMOUNT');
  }

  const conn = await db.beginTransaction();
  try {
    // 确定新状态
    let newStatus;
    if (action === 'approve') {
      newStatus = refund.type === 'only_refund' ? 'refunding' : 'awaiting_return';
    } else {
      newStatus = 'rejected';
    }

    // 更新售后单状态（CAS 防并发：仅当 status='pending' 时更新）
    const updateResult = await conn.execute(
      'UPDATE refund_requests ' +
      'SET status = ?, merchant_review_reason = ?, updated_at = NOW() ' +
      "WHERE id = ? AND status = 'pending'",
      [newStatus, reason, refundRequestId]
    );

    if (updateResult.affectedRows === 0) {
      await db.rollback(conn);
      throw new Error('INVALID_STATUS');
    }

    // 记录操作日志
    const logAction = action === 'approve' ? 'merchant_approve' : 'merchant_reject';
    const logDetail = action === 'approve'
      ? '商家同意' + (refund.type === 'only_refund' ? '仅退款' : '退货退款') + '申请'
      : '商家拒绝: ' + (reason || '');

    await conn.execute(
      'INSERT INTO refund_logs (refund_request_id, operator_id, action, detail, created_at) ' +
      'VALUES (?, ?, ?, ?, NOW())',
      [refundRequestId, userId, logAction, logDetail]
    );

    await db.commit(conn);

    // 查询更新后的完整售后单返回
    const updatedRows = await db.query(
      'SELECT rr.*, so.sub_order_no, o.order_no ' +
      'FROM refund_requests rr ' +
      'JOIN sub_orders so ON rr.sub_order_id = so.id ' +
      'JOIN orders o ON so.order_id = o.id ' +
      'WHERE rr.id = ?',
      [refundRequestId]
    );

    return updatedRows[0];
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = { getMerchantRefundList, approveRefund };

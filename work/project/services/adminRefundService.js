const db = require('../config/db');

/**
 * 获取仲裁工单列表
 * @param {Object} filters - { page, pageSize, status, requestNo }
 * @returns {Object} { list, total, page, pageSize }
 */
async function getArbitrationList({ page = 1, pageSize = 20, status, requestNo } = {}) {
  const offset = (page - 1) * pageSize;
  let where = 'WHERE rr.status = ?';
  const params = [status || 'arbitrating'];

  if (requestNo) {
    where += ' AND rr.request_no LIKE ?';
    params.push(`%${requestNo}%`);
  }
  const countSql = 'SELECT COUNT(*) as total FROM refund_requests rr ' + where;
  const countResult = await db.query(countSql, params);
  const total = countResult[0].total;

  const sql =
    'SELECT ' +
    'rr.id, rr.request_no, rr.sub_order_id, rr.user_id, rr.type, ' +
    'rr.reason, rr.amount, rr.evidence_images, rr.status, ' +
    'rr.merchant_review_reason, rr.arbitration_ruling, ' +
    'rr.created_at, rr.updated_at, ' +
    'u.nickname AS user_nickname, u.mobile AS user_mobile, ' +
    'so.sub_order_no, so.amount AS sub_order_amount, so.shop_id, ' +
    'o.order_no, o.total_amount AS order_total_amount, ' +
    's.name AS shop_name ' +
    'FROM refund_requests rr ' +
    'LEFT JOIN users u ON rr.user_id = u.id ' +
    'LEFT JOIN sub_orders so ON rr.sub_order_id = so.id ' +
    'LEFT JOIN orders o ON so.order_id = o.id ' +
    'LEFT JOIN shops s ON so.shop_id = s.id ' +
    where + ' ' +
    'ORDER BY rr.created_at DESC ' +
    'LIMIT ? OFFSET ?';

  const list = await db.query(sql, [...params, pageSize, offset]);

  return { list, total, page, pageSize };
}

/**
 * 执行仲裁裁决
 * @param {number} refundRequestId - 售后申请ID
 * @param {Object} rulingData - { ruling: 'force_refund'|'dismiss', reason }
 * @param {number} adminId - 管理员ID
 * @returns {Object} { id, status, arbitration_ruling }
 */
async function arbitrateRefund(refundRequestId, { ruling, reason }, adminId) {
  // 校验裁决类型
  if (!['force_refund', 'dismiss'].includes(ruling)) {
    throw new Error('INVALID_RULING');
  }

  const conn = await db.beginTransaction();
  try {
    // 悲观锁读取售后申请
    const [refundRequest] = await conn.execute(
      'SELECT id, status FROM refund_requests WHERE id = ? FOR UPDATE',
      [refundRequestId]
    );

    if (!refundRequest) {
      await db.rollback(conn);
      throw new Error('NOT_FOUND');
    }

    // 只允许仲裁中的申请
    if (refundRequest.status !== 'arbitrating') {
      await db.rollback(conn);
      throw new Error('INVALID_STATUS');
    }

    const newStatus = ruling === 'force_refund' ? 'refunding' : 'closed';

    // 更新售后申请状态 + 仲裁裁决理由
    await conn.execute(
      'UPDATE refund_requests SET status = ?, arbitration_ruling = ?, updated_at = NOW() WHERE id = ?',
      [newStatus, reason || null, refundRequestId]
    );

    // 写入售后操作日志
    await conn.execute(
      'INSERT INTO refund_logs (refund_request_id, operator_id, action, detail) VALUES (?, ?, ?, ?)',
      [
        refundRequestId,
        adminId,
        ruling === 'force_refund' ? 'admin_force_refund' : 'admin_dismiss',
        reason || null
      ]
    );

    // 写入运营操作日志
    await conn.execute(
      'INSERT INTO operation_logs (admin_id, action, target_type, target_id, detail) VALUES (?, ?, ?, ?, ?)',
      [
        adminId,
        'arbitrate_refund',
        'refund_request',
        refundRequestId,
        JSON.stringify({ ruling, reason: reason || '', newStatus })
      ]
    );

    await db.commit(conn);

    return {
      id: refundRequestId,
      status: newStatus,
      arbitration_ruling: reason || null
    };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = { getArbitrationList, arbitrateRefund };

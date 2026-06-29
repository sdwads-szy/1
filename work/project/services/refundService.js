const db = require('../config/db');

/**
 * 买家申请退款
 * @param {number} userId - 用户 ID
 * @param {number} orderId - 订单 ID
 * @param {string} reason - 退款原因
 * @param {string} amount - 退款金额（DECIMAL 字符串）
 * @param {string[]} [evidenceImages] - 凭证图片 URL 数组
 * @returns {Promise<{refundId: number, status: string}>}
 */
async function applyRefund(userId, orderId, reason, amount, evidenceImages) {
  const conn = await db.beginTransaction();
  try {
    // 1. 查询支付单，确认已支付
    const [payments] = await conn.execute(
      'SELECT * FROM payments WHERE order_id = ? AND status = ?',
      [orderId, 'paid']
    );
    if (!payments.length) {
      await db.rollback(conn);
      throw new Error('ORDER_NOT_REFUNDABLE');
    }
    const payment = payments[0];
    const payAmount = parseFloat(payment.amount);
    const refundAmount = parseFloat(amount);

    // 2. 校验退款金额不超过原支付金额
    if (refundAmount > payAmount) {
      await db.rollback(conn);
      throw new Error('AMOUNT_EXCEED');
    }

    // 3. 幂等检查：该订单是否已有进行中的退款
    const [existing] = await conn.execute(
      "SELECT id FROM refunds WHERE order_id = ? AND status NOT IN ('rejected', 'completed')",
      [orderId]
    );
    if (existing.length) {
      await db.rollback(conn);
      throw new Error('REFUND_DUPLICATE');
    }

    // 4. 获取订单的商家 ID（shop_id）
    const [orders] = await conn.execute(
      'SELECT shop_id FROM orders WHERE id = ?',
      [orderId]
    );
    if (!orders.length) {
      await db.rollback(conn);
      throw new Error('ORDER_NOT_FOUND');
    }
    const merchantId = orders[0].shop_id;

    // 5. 序列化凭证图片
    const evidenceJson = evidenceImages && evidenceImages.length > 0
      ? JSON.stringify(evidenceImages)
      : null;

    // 6. 创建退款单
    const [result] = await conn.execute(
      `INSERT INTO refunds (order_id, payment_id, user_id, merchant_id, reason, amount, evidence_images, status)
       VALUES (?, ?, ?, ?, ?, ?, ?, 'applied')`,
      [orderId, payment.id, userId, merchantId, reason, amount, evidenceJson]
    );

    await db.commit(conn);
    return { refundId: result.insertId, status: 'applied' };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 获取用户的退款列表
 * @param {number} userId
 * @returns {Promise<Array>}
 */
async function getUserRefunds(userId) {
  const rows = await db.query(
    `SELECT r.id, r.order_id AS orderId, r.payment_id AS paymentId,
            r.amount, r.status, r.reason,
            r.apply_at AS applyAt, r.processed_at AS processedAt,
            r.completed_at AS completedAt, r.evidence_images AS evidenceImages
     FROM refunds r
     WHERE r.user_id = ?
     ORDER BY r.created_at DESC`,
    [userId]
  );
  // 确保 evidenceImages 为数组
  return rows.map(row => {
    if (typeof row.evidenceImages === 'string') {
      try { row.evidenceImages = JSON.parse(row.evidenceImages); } catch (_) { row.evidenceImages = null; }
    }
    return row;
  });
}

/**
 * 获取退款详情
 * @param {number} refundId
 * @returns {Promise<Object>}
 */
async function getRefundById(refundId) {
  const rows = await db.query(
    `SELECT r.id, r.order_id AS orderId, r.payment_id AS paymentId,
            r.user_id AS userId, r.merchant_id AS merchantId,
            r.reason, r.amount, r.evidence_images AS evidenceImages,
            r.status, r.apply_at AS applyAt,
            r.processed_at AS processedAt, r.completed_at AS completedAt,
            r.created_at AS createdAt
     FROM refunds r
     WHERE r.id = ?`,
    [refundId]
  );
  if (!rows.length) throw new Error('REFUND_NOT_FOUND');

  const refund = rows[0];
  if (typeof refund.evidenceImages === 'string') {
    try { refund.evidenceImages = JSON.parse(refund.evidenceImages); } catch (_) { refund.evidenceImages = null; }
  }
  return refund;
}

/**
 * 管理员查看退款列表（支持状态筛选 + 分页）
 * @param {Object} filters - { status?, page?, pageSize? }
 * @returns {Promise<{list: Array, total: number, page: number, pageSize: number}>}
 */
async function listRefunds(filters = {}) {
  const { status, page, pageSize } = filters;
  const safePage = parseInt(page) || 1;
  const safePageSize = parseInt(pageSize) || 20;
  const offset = (safePage - 1) * safePageSize;

  let whereClause = '';
  const params = [];

  if (status) {
    whereClause = 'WHERE r.status = ?';
    params.push(status);
  }

  const countRows = await db.query(
    `SELECT COUNT(*) AS total FROM refunds r ${whereClause}`,
    params
  );
  const total = countRows[0].total;

  const rows = await db.query(
    `SELECT r.id, r.order_id AS orderId, r.payment_id AS paymentId,
            r.user_id AS userId, r.merchant_id AS merchantId,
            r.reason, r.amount, r.status,
            r.apply_at AS applyAt, r.processed_at AS processedAt,
            r.completed_at AS completedAt, r.evidence_images AS evidenceImages
     FROM refunds r ${whereClause}
     ORDER BY r.created_at DESC
     LIMIT ? OFFSET ?`,
    [...params, safePageSize, offset]
  );

  return {
    list: rows.map(row => {
      if (typeof row.evidenceImages === 'string') {
        try { row.evidenceImages = JSON.parse(row.evidenceImages); } catch (_) { row.evidenceImages = null; }
      }
      return row;
    }),
    total,
    page: safePage,
    pageSize: safePageSize
  };
}

/**
 * 商家审批退款
 * @param {number} refundId - 退款单 ID
 * @param {number} merchantId - 商家用户 ID
 * @param {'approved'|'rejected'} action - 审批操作
 * @param {string} [note] - 审批备注（当前 DDL 无 note 列，仅用于日志）
 * @returns {Promise<{refundStatus: string}>}
 */
async function approveRefund(refundId, merchantId, action, note) {
  const rows = await db.query(
    'SELECT * FROM refunds WHERE id = ?',
    [refundId]
  );
  if (!rows.length) throw new Error('REFUND_NOT_FOUND');

  const refund = rows[0];

  // 校验商家所有权
  if (refund.merchant_id !== merchantId) {
    throw new Error('NOT_MERCHANT_OWNER');
  }

  // 校验状态：只有 applied 状态可审批
  if (refund.status !== 'applied') {
    throw new Error('ALREADY_PROCESSED');
  }

  const newStatus = action === 'approved' ? 'approved' : 'rejected';
  await db.query(
    'UPDATE refunds SET status = ?, processed_at = NOW() WHERE id = ?',
    [newStatus, refundId]
  );

  return { refundStatus: newStatus };
}

/**
 * 执行退款（平台管理员调用支付网关原路退款，含指数退避重试）
 * @param {number} refundId
 * @returns {Promise<{refundStatus: string}>}
 */
async function executeRefund(refundId) {
  const rows = await db.query(
    'SELECT * FROM refunds WHERE id = ?',
    [refundId]
  );
  if (!rows.length) throw new Error('REFUND_NOT_FOUND');

  const refund = rows[0];

  // 幂等：已完成则直接返回
  if (refund.status === 'completed') {
    return { refundStatus: 'completed' };
  }

  // 只有 approved 或 processing（上次执行中断）可执行
  if (refund.status !== 'approved' && refund.status !== 'processing') {
    throw new Error('REFUND_NOT_APPROVED');
  }

  // 标记为处理中
  await db.query(
    "UPDATE refunds SET status = 'processing' WHERE id = ?",
    [refundId]
  );

  // 查询支付单信息
  const [paymentRows] = await db.query(
    'SELECT * FROM payments WHERE id = ?',
    [refund.payment_id]
  );
  // db.query already destructured — rows is directly the array
  const payment = Array.isArray(paymentRows) ? paymentRows[0] : paymentRows;

  // 调用支付网关退款（最多重试 3 次，指数退避）
  let gatewaySuccess = false;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const gatewayResult = await callRefundGateway(payment, refund.amount);
      if (gatewayResult.success) {
        gatewaySuccess = true;
        break;
      }
    } catch (_) {
      // 网关调用异常，记录并准备重试
    }
    if (attempt < 2) {
      const delayMs = Math.pow(2, attempt) * 2000; // 2s → 4s → 8s
      await sleep(delayMs);
    }
  }

  if (!gatewaySuccess) {
    // 3 次均失败，恢复为 approved 等待人工介入
    await db.query(
      "UPDATE refunds SET status = 'approved' WHERE id = ?",
      [refundId]
    );
    throw new Error('GATEWAY_REFUND_FAIL');
  }

  // 网关成功 → 事务内更新退款单 + 支付单
  const conn = await db.beginTransaction();
  try {
    await conn.execute(
      "UPDATE refunds SET status = 'completed', completed_at = NOW() WHERE id = ?",
      [refundId]
    );

    const refundAmount = parseFloat(refund.amount);
    await conn.execute(
      "UPDATE payments SET status = 'refunded', refund_amount = refund_amount + ? WHERE id = ?",
      [refundAmount, refund.payment_id]
    );

    await db.commit(conn);
    return { refundStatus: 'completed' };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 模拟调用支付网关退款接口
 * @param {Object} payment - 支付单记录
 * @param {string} refundAmount - 退款金额
 * @returns {Promise<{success: boolean, gatewayRefundNo?: string}>}
 */
async function callRefundGateway(payment, refundAmount) {
  // 生产环境对接微信/支付宝退款 API
  // 此处模拟：绝大多数情况成功
  const simulatedSuccess = Math.random() > 0.05; // 95% 成功率用于模拟
  if (!simulatedSuccess) {
    throw new Error('GATEWAY_TIMEOUT');
  }
  return {
    success: true,
    gatewayRefundNo: 'rf_' + Date.now() + '_' + Math.random().toString(36).substring(2, 10)
  };
}

/**
 * 延时工具函数
 * @param {number} ms
 * @returns {Promise<void>}
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

module.exports = {
  applyRefund,
  getUserRefunds,
  getRefundById,
  listRefunds,
  approveRefund,
  executeRefund
};

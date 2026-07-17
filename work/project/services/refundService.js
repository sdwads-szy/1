const db = require('../config/db');
const snowflake = require('../utils/snowflake');

/**
 * 生成售后单号 RF + 10 位雪花ID尾数
 */
function generateRequestNo() {
  const id = String(snowflake.nextId());
  return 'RF' + id.slice(-10);
}

// ═══════════════════════════════════════════════════════════
// 消费者 — 申请售后
// ═══════════════════════════════════════════════════════════

/**
 * 创建售后申请
 * @param {number} userId - 申请人用户ID
 * @param {object} data - { subOrderId, type, reason, amount, evidenceImages }
 * @returns {object} 创建的售后单
 */
async function createRefundRequest(userId, data) {
  const { subOrderId, type, reason, amount, evidenceImages } = data;

  // 1. 查询子订单 & 验证归属
  const subOrders = await db.query(
    `SELECT so.id, so.order_id, so.shop_id, so.amount, so.status
     FROM sub_orders so
     WHERE so.id = ?`,
    [subOrderId]
  );
  if (!subOrders.length) throw new Error('SUB_ORDER_NOT_FOUND');
  const subOrder = subOrders[0];

  // 2. 验证订单归属
  const orders = await db.query(
    'SELECT o.user_id FROM orders o WHERE o.id = ?',
    [subOrder.order_id]
  );
  if (!orders.length || orders[0].user_id !== userId) {
    throw new Error('FORBIDDEN');
  }

  // 3. 校验子订单状态允许售后
  const allowedStatuses = ['paid', 'shipped', 'completed'];
  if (!allowedStatuses.includes(subOrder.status)) {
    throw new Error('ORDER_STATUS_NOT_ALLOWED');
  }

  // 4. 检查是否已有进行中的售后单
  const activeRefunds = await db.query(
    `SELECT id FROM refund_requests
     WHERE sub_order_id = ?
       AND status NOT IN ('completed', 'closed')`,
    [subOrderId]
  );
  if (activeRefunds.length) throw new Error('ALREADY_REFUNDING');

  // 5. 校验金额不超过实付
  if (amount > parseFloat(subOrder.amount)) {
    throw new Error('EXCEED_AMOUNT');
  }

  // 6. 写入售后单 + 操作日志（事务）
  const requestNo = generateRequestNo();
  const conn = await db.beginTransaction();
  try {
    const [result] = await conn.execute(
      `INSERT INTO refund_requests
        (request_no, sub_order_id, user_id, type, reason, amount, evidence_images, status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        requestNo,
        subOrderId,
        userId,
        type,
        reason,
        amount,
        evidenceImages && evidenceImages.length ? JSON.stringify(evidenceImages) : null,
        'pending',
      ]
    );

    await conn.execute(
      `INSERT INTO refund_logs (refund_request_id, operator_id, action, detail)
       VALUES (?, ?, ?, ?)`,
      [result.insertId, userId, 'apply', '用户申请售后']
    );

    await db.commit(conn);

    return {
      id: result.insertId,
      request_no: requestNo,
      sub_order_id: subOrderId,
      user_id: userId,
      type,
      reason,
      amount,
      evidence_images: evidenceImages || [],
      status: 'pending',
    };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

// ═══════════════════════════════════════════════════════════
// 通用 — 查询售后详情
// ═══════════════════════════════════════════════════════════

/**
 * 查询售后单详情（含操作日志 + 店铺信息），按角色鉴权
 * @param {number} refundId
 * @param {number} userId
 * @param {string} role - user / merchant / admin
 */
async function getRefundRequest(refundId, userId, role) {
  const rows = await db.query(
    `SELECT rr.*,
            so.order_id, so.sub_order_no, so.shop_id, so.amount AS sub_order_amount,
            s.name AS shop_name
     FROM refund_requests rr
     JOIN sub_orders so ON so.id = rr.sub_order_id
     JOIN shops s ON s.id = so.shop_id
     WHERE rr.id = ?`,
    [refundId]
  );
  if (!rows.length) throw new Error('REFUND_NOT_FOUND');
  const refund = rows[0];

  // 角色鉴权
  if (role === 'user' && refund.user_id !== userId) {
    throw new Error('FORBIDDEN');
  }
  if (role === 'merchant') {
    const merchantRows = await db.query(
      `SELECT m.id FROM merchants m
       JOIN shops s ON s.merchant_id = m.id
       WHERE s.id = ? AND m.user_id = ?`,
      [refund.shop_id, userId]
    );
    if (!merchantRows.length) throw new Error('FORBIDDEN');
  }
  // admin 可查看全部

  // 查询操作日志
  const logs = await db.query(
    `SELECT rl.id, rl.action, rl.detail, rl.created_at,
            u.nickname AS operator_name
     FROM refund_logs rl
     LEFT JOIN users u ON u.id = rl.operator_id
     WHERE rl.refund_request_id = ?
     ORDER BY rl.created_at ASC`,
    [refundId]
  );

  return { ...refund, logs };
}

/**
 * 按 ID 查询售后单（内部使用，不做角色鉴权）
 */
async function getRefundRequestById(refundId) {
  const rows = await db.query(
    'SELECT * FROM refund_requests WHERE id = ?',
    [refundId]
  );
  if (!rows.length) throw new Error('REFUND_NOT_FOUND');
  return rows[0];
}

// ═══════════════════════════════════════════════════════════
// 商家 — 审批售后
// ═══════════════════════════════════════════════════════════

/**
 * 商家同意/拒绝售后
 * @param {number} refundId
 * @param {number} merchantUserId - 商家登录用户ID
 * @param {string} action - 'approve' | 'reject'
 * @param {string|null} reason - 审批备注
 */
async function approveRefundRequest(refundId, merchantUserId, action, reason) {
  // 1. 获取商家 merchant_id
  const merchantRows = await db.query(
    'SELECT m.id FROM merchants m WHERE m.user_id = ?',
    [merchantUserId]
  );
  if (!merchantRows.length) throw new Error('FORBIDDEN');
  const merchantId = merchantRows[0].id;

  // 2. 查询售后单 & 验证归属
  const refund = await getRefundRequestById(refundId);

  const shopRows = await db.query(
    `SELECT s.merchant_id FROM sub_orders so
     JOIN shops s ON s.id = so.shop_id
     WHERE so.id = ?`,
    [refund.sub_order_id]
  );
  if (!shopRows.length || shopRows[0].merchant_id !== merchantId) {
    throw new Error('FORBIDDEN');
  }

  // 3. 状态校验：只有 pending 可审批
  if (refund.status !== 'pending') {
    throw new Error('STATUS_CONFLICT');
  }

  // 4. 执行审批
  const conn = await db.beginTransaction();
  try {
    let newStatus;
    if (action === 'approve') {
      // 仅退款 → 直接进入退款流程；退货退款 → 等待买家退货
      newStatus = refund.type === 'only_refund' ? 'refunding' : 'awaiting_return';
    } else {
      newStatus = 'rejected';
    }

    const [updateResult] = await conn.execute(
      `UPDATE refund_requests
       SET status = ?, merchant_review_reason = ?
       WHERE id = ? AND status = 'pending'`,
      [newStatus, reason, refundId]
    );
    if (updateResult.affectedRows === 0) {
      await db.rollback(conn);
      throw new Error('STATUS_CONFLICT');
    }

    const logAction = action === 'approve' ? 'merchant_approve' : 'merchant_reject';
    await conn.execute(
      `INSERT INTO refund_logs (refund_request_id, operator_id, action, detail)
       VALUES (?, ?, ?, ?)`,
      [refundId, merchantUserId, logAction, reason || '']
    );

    // 同意 + 仅退款 → 立即执行退款
    if (action === 'approve' && refund.type === 'only_refund') {
      await processRefundInternal(conn, refund);
    }

    await db.commit(conn);
    return { id: refundId, status: newStatus };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 商家售后列表
 */
async function listMerchantRefunds(merchantUserId, filters) {
  const { status, page, pageSize } = filters;
  const offset = (page - 1) * pageSize;

  const merchantRows = await db.query(
    'SELECT m.id FROM merchants m WHERE m.user_id = ?',
    [merchantUserId]
  );
  if (!merchantRows.length) throw new Error('FORBIDDEN');
  const merchantId = merchantRows[0].id;

  let where = 'WHERE s.merchant_id = ?';
  const params = [merchantId];

  if (status) {
    where += ' AND rr.status = ?';
    params.push(status);
  }

  const countSql = `SELECT COUNT(*) AS total
    FROM refund_requests rr
    JOIN sub_orders so ON so.id = rr.sub_order_id
    JOIN shops s ON s.id = so.shop_id
    ${where}`;
  const countResult = await db.query(countSql, params);

  const listSql = `SELECT rr.*, so.sub_order_no, so.order_id,
            u.nickname AS user_nickname
     FROM refund_requests rr
     JOIN sub_orders so ON so.id = rr.sub_order_id
     JOIN shops s ON s.id = so.shop_id
     JOIN users u ON u.id = rr.user_id
     ${where}
     ORDER BY rr.created_at DESC
     LIMIT ? OFFSET ?`;
  const listParams = [...params, pageSize, offset];
  const rows = await db.query(listSql, listParams);

  return {
    list: rows,
    total: countResult[0].total,
    page,
    pageSize,
  };
}

// ═══════════════════════════════════════════════════════════
// 平台 — 仲裁
// ═══════════════════════════════════════════════════════════

/**
 * 仲裁工单列表（状态为 rejected / arbitrating）
 */
async function listArbitrationRefunds(filters) {
  const { status, page, pageSize } = filters;
  const offset = (page - 1) * pageSize;

  let where = "WHERE rr.status IN ('rejected', 'arbitrating')";
  const params = [];

  if (status) {
    where += ' AND rr.status = ?';
    params.push(status);
  }

  const countSql = `SELECT COUNT(*) AS total
    FROM refund_requests rr
    ${where}`;
  const countResult = await db.query(countSql, params);

  const listSql = `SELECT rr.*,
            so.sub_order_no, so.order_id,
            u.nickname AS user_nickname,
            s.name AS shop_name
     FROM refund_requests rr
     JOIN sub_orders so ON so.id = rr.sub_order_id
     JOIN shops s ON s.id = so.shop_id
     JOIN users u ON u.id = rr.user_id
     ${where}
     ORDER BY rr.created_at DESC
     LIMIT ? OFFSET ?`;
  const listParams = [...params, pageSize, offset];
  const rows = await db.query(listSql, listParams);

  return {
    list: rows,
    total: countResult[0].total,
    page,
    pageSize,
  };
}

/**
 * 平台仲裁裁决
 * @param {number} refundId
 * @param {number} adminUserId
 * @param {string} ruling - 'force_refund' | 'dismiss'
 * @param {string|null} reason
 */
async function arbitrateRefund(refundId, adminUserId, ruling, reason) {
  const refund = await getRefundRequestById(refundId);

  if (!['rejected', 'arbitrating'].includes(refund.status)) {
    throw new Error('STATUS_CONFLICT');
  }

  const conn = await db.beginTransaction();
  try {
    let newStatus;
    if (ruling === 'force_refund') {
      newStatus = 'refunding';
    } else {
      newStatus = 'closed';
    }

    const [updateResult] = await conn.execute(
      `UPDATE refund_requests
       SET status = ?, arbitration_ruling = ?
       WHERE id = ? AND status IN ('rejected', 'arbitrating')`,
      [newStatus, reason, refundId]
    );
    if (updateResult.affectedRows === 0) {
      await db.rollback(conn);
      throw new Error('STATUS_CONFLICT');
    }

    await conn.execute(
      `INSERT INTO refund_logs (refund_request_id, operator_id, action, detail)
       VALUES (?, ?, ?, ?)`,
      [refundId, adminUserId, 'arbitrate', `${ruling}: ${reason || ''}`]
    );

    // 强制退款 → 执行退款流程
    if (ruling === 'force_refund') {
      await processRefundInternal(conn, refund);
    }

    await db.commit(conn);
    return { id: refundId, status: newStatus };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

// ═══════════════════════════════════════════════════════════
// 内部 — 执行退款
// ═══════════════════════════════════════════════════════════

/**
 * 执行实际退款操作（在已有事务中调用）
 * - 更新 payment 状态为 refunded
 * - 更新 sub_order 状态为 refunding
 * - 更新 order 状态
 * - return_refund 类型恢复库存
 * - 从商家钱包扣款
 *
 * @param {object} conn - 事务连接
 * @param {object} refund - 售后单记录
 */
async function processRefundInternal(conn, refund) {
  // 1. 查询子订单
  const [subOrderRows] = await conn.execute(
    `SELECT so.*, o.id AS order_id
     FROM sub_orders so
     JOIN orders o ON o.id = so.order_id
     WHERE so.id = ?`,
    [refund.sub_order_id]
  );
  if (!subOrderRows.length) return;
  const subOrder = subOrderRows[0];

  // 2. 更新支付记录
  await conn.execute(
    `UPDATE payments SET status = 'refunded'
     WHERE sub_order_id = ? AND status = 'success'`,
    [refund.sub_order_id]
  );

  // 3. 更新子订单状态
  await conn.execute(
    `UPDATE sub_orders SET status = 'refunding'
     WHERE id = ? AND status IN ('paid', 'shipped', 'completed')`,
    [refund.sub_order_id]
  );

  // 4. 更新主订单状态
  await conn.execute(
    `UPDATE orders SET status = 'refunding'
     WHERE id = ? AND status NOT IN ('cancelled', 'refunded')`,
    [subOrder.order_id]
  );

  // 5. 退货退款 → 恢复库存
  if (refund.type === 'return_refund') {
    const [items] = await conn.execute(
      'SELECT oi.sku_id, oi.quantity FROM order_items oi WHERE oi.sub_order_id = ?',
      [refund.sub_order_id]
    );
    for (const item of items) {
      await conn.execute(
        `UPDATE inventories
         SET stock = stock + ?, version = version + 1
         WHERE sku_id = ? AND shop_id = ?`,
        [item.quantity, item.sku_id, subOrder.shop_id]
      );
    }
  }

  // 6. 扣除商家钱包余额
  const [walletRows] = await conn.execute(
    `SELECT mw.id, mw.balance, mw.version
     FROM merchant_wallets mw
     JOIN shops s ON s.merchant_id = mw.merchant_id
     WHERE s.id = ?
     FOR UPDATE`,
    [subOrder.shop_id]
  );
  if (walletRows.length > 0) {
    const wallet = walletRows[0];
    const newBalance = parseFloat(wallet.balance) - parseFloat(refund.amount);
    await conn.execute(
      `UPDATE merchant_wallets
       SET balance = ?, version = version + 1
       WHERE id = ? AND version = ?`,
      [Math.max(0, newBalance), wallet.id, wallet.version]
    );
  }

  // 7. 记录系统操作日志
  await conn.execute(
    `INSERT INTO refund_logs (refund_request_id, operator_id, action, detail)
     VALUES (?, ?, ?, ?)`,
    [refund.id, 0, 'system_refund', '系统执行退款']
  );
}

module.exports = {
  createRefundRequest,
  getRefundRequest,
  getRefundRequestById,
  approveRefundRequest,
  listMerchantRefunds,
  listArbitrationRefunds,
  arbitrateRefund,
};

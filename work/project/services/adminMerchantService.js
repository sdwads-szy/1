const db = require('../config/db');

// ============================================================
//  商家列表查询
// ============================================================

/**
 * 平台商家列表（JOIN shops 获取店铺名）
 * @param {string|null} status — 状态筛选，null=全部
 * @param {number} page
 * @param {number} pageSize
 * @returns {{list: Array, total: number, page: number, pageSize: number}}
 */
async function getMerchantsList(status, page, pageSize) {
  const statusFilter = status || null;
  const offset = (page - 1) * pageSize;

  // 校验 status 枚举值
  if (status && !['pending_review', 'approved', 'disabled'].includes(status)) {
    status = null;
  }

  const dataSql = 'SELECT m.id, m.user_id, m.credit_code, m.contact_name, m.contact_mobile, ' +
    'm.status, m.created_at, s.name AS shop_name ' +
    'FROM merchants m ' +
    'LEFT JOIN shops s ON s.merchant_id = m.id ' +
    'WHERE (? IS NULL OR m.status = ?) ' +
    'ORDER BY m.created_at DESC ' +
    'LIMIT ? OFFSET ?';

  const countSql = 'SELECT COUNT(*) AS total FROM merchants WHERE (? IS NULL OR status = ?)';

  const [rows, countRows] = await Promise.all([
    db.query(dataSql, [statusFilter, statusFilter, pageSize, offset]),
    db.query(countSql, [statusFilter, statusFilter]),
  ]);

  return {
    list: rows,
    total: countRows[0].total,
    page,
    pageSize,
  };
}

// ============================================================
//  商家入驻审核
// ============================================================

/**
 * 平台审核商家入驻：通过→shop开业+日志，驳回→记录原因+日志
 * @param {number} adminId — 管理员用户ID
 * @param {number} merchantId — 商家ID
 * @param {string} action — 'approve' | 'reject'
 * @param {string|null} reason — 审核意见，驳回时必填
 * @returns {{merchantId: number, status: string}}
 */
async function reviewMerchant(adminId, merchantId, action, reason) {
  // Step 1: 查询商家，仅 pending_review 状态可操作
  const merchants = await db.query(
    'SELECT id, status FROM merchants WHERE id = ?',
    [merchantId]
  );
  if (!merchants.length) {
    throw new Error('MERCHANT_NOT_FOUND');
  }

  const merchant = merchants[0];

  // Step 2: 幂等守卫 — 已审核过的拒绝重复操作
  if (merchant.status !== 'pending_review') {
    throw new Error('ALREADY_REVIEWED');
  }

  const newStatus = action === 'approve' ? 'approved' : 'disabled';
  const shopStatus = action === 'approve' ? 'open' : 'closed';

  // Step 3-6: 事务内完成审核
  const conn = await db.beginTransaction();
  try {
    // Step 3: 更新商家状态
    await conn.execute(
      'UPDATE merchants SET status = ?, review_reason = ?, reviewed_at = NOW() WHERE id = ?',
      [newStatus, reason, merchantId]
    );

    // Step 4: 通过→店铺开业；驳回→店铺关闭
    await conn.execute(
      'UPDATE shops SET status = ? WHERE merchant_id = ?',
      [shopStatus, merchantId]
    );

    // Step 5: 运营审计日志
    await conn.execute(
      'INSERT INTO operation_logs (admin_id, action, target_type, target_id, detail) VALUES (?, ?, ?, ?, ?)',
      [
        adminId,
        'review_merchant',
        'merchant',
        merchantId,
        JSON.stringify({
          before: 'pending_review',
          after: newStatus,
          reason: reason || '',
        }),
      ]
    );

    // Step 6: 提交
    await db.commit(conn);

    // 异步：邮件通知（失败不阻塞主流程）
    sendMerchantReviewNotification(merchantId, action, reason).catch(() => {
      // 邮件通知失败，静默忽略
    });

    return { merchantId, status: newStatus };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

// ============================================================
//  冻结/解冻商家
// ============================================================

/**
 * 冻结/解冻商家：冻结→联动店铺frozen+商品下架
 * @param {number} adminId — 管理员用户ID
 * @param {number} merchantId — 商家ID
 * @param {string} action — 'freeze' | 'unfreeze'
 * @returns {{merchantId: number, status: string}}
 */
async function freezeMerchant(adminId, merchantId, action) {
  // Step 1: 查询商家是否存在
  const merchants = await db.query(
    'SELECT id, status FROM merchants WHERE id = ?',
    [merchantId]
  );
  if (!merchants.length) {
    throw new Error('MERCHANT_NOT_FOUND');
  }

  const merchant = merchants[0];

  // Step 2: 状态转换校验
  const newMerchantStatus = action === 'freeze' ? 'disabled' : 'approved';
  const newShopStatus = action === 'freeze' ? 'frozen' : 'open';

  if (action === 'freeze' && merchant.status !== 'approved') {
    throw new Error('INVALID_ACTION');
  }
  if (action === 'unfreeze' && merchant.status !== 'disabled') {
    throw new Error('INVALID_ACTION');
  }

  // Step 3-4: 事务
  const conn = await db.beginTransaction();
  try {
    // 更新商家状态
    await conn.execute(
      'UPDATE merchants SET status = ? WHERE id = ?',
      [newMerchantStatus, merchantId]
    );

    // 联动更新店铺状态
    await conn.execute(
      'UPDATE shops SET status = ? WHERE merchant_id = ?',
      [newShopStatus, merchantId]
    );

    // Step 3.1: 联动下架该商家所有商品
    await conn.execute(
      "UPDATE spu SET status = 'delisted' WHERE shop_id IN (SELECT id FROM shops WHERE merchant_id = ?)",
      [merchantId]
    );

    // 运营审计日志
    const logAction = action === 'freeze' ? 'freeze_merchant' : 'unfreeze_merchant';
    await conn.execute(
      'INSERT INTO operation_logs (admin_id, action, target_type, target_id, detail) VALUES (?, ?, ?, ?, ?)',
      [
        adminId,
        logAction,
        'merchant',
        merchantId,
        JSON.stringify({
          before: merchant.status,
          after: newMerchantStatus,
        }),
      ]
    );

    await db.commit(conn);

    return { merchantId, status: newMerchantStatus };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

// ============================================================
//  邮件通知（mock 实现，异步不阻塞主流程）
// ============================================================

/**
 * 审核结果邮件通知
 * mock 模式：仅记录日志
 * real 模式：调用 SMTP 发送（通过 process.env.SMTP_* 配置）
 */
async function sendMerchantReviewNotification(merchantId, action, reason) {
  const EMAIL_MODE = process.env.EMAIL_MODE || 'mock';

  if (EMAIL_MODE === 'mock') {
    // mock: 仅记录日志
    const logger = require('../config/logger');
    logger.info(
      `[MOCK EMAIL] 商家审核通知 — merchantId=${merchantId}, action=${action}, reason="${reason || ''}"`
    );
    return;
  }

  // real: 调用 SMTP 发送（预留，当前 mock 阶段不实现完整 SMTP）
  // const transporter = nodemailer.createTransport({...});
  // await transporter.sendMail({...});
}

module.exports = { getMerchantsList, reviewMerchant, freezeMerchant };

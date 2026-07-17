const db = require('../config/db');

const SENSITIVE_WORD_MODE = process.env.SENSITIVE_WORD_MODE || 'mock';

/**
 * 查询商品列表（管理员视角，按状态筛选）
 * @param {string} status - 商品状态 draft|listed|delisted
 * @param {number} page
 * @param {number} pageSize
 * @returns {{list, total, page, pageSize}}
 */
async function listProducts(status, page, pageSize) {
  const offset = (page - 1) * pageSize;

  let whereClause = '';
  const params = [];
  const countParams = [];

  if (status) {
    whereClause = ' WHERE status = ?';
    params.push(status);
    countParams.push(status);
  }

  const sql = `SELECT id, shop_id, category_id, name, default_image, status, sales, created_at, updated_at FROM spu${whereClause} ORDER BY updated_at DESC LIMIT ? OFFSET ?`;
  const countSql = `SELECT COUNT(*) AS total FROM spu${whereClause}`;

  params.push(pageSize, offset);

  const [rows, countResult] = await Promise.all([
    db.query(sql, params),
    db.query(countSql, countParams)
  ]);

  return {
    list: rows,
    total: countResult[0].total,
    page,
    pageSize
  };
}

/**
 * 审核商品：敏感词过滤 → 通过上架 / 驳回回退 → 写运营日志
 * @param {number} adminId - 管理员用户ID
 * @param {number} productId - 商品SPU ID
 * @param {string} action - approve|reject
 * @param {string} [reason] - 驳回原因
 * @returns {{productId, status}}
 */
async function reviewProduct(adminId, productId, action, reason) {
  // 校验 action
  if (!['approve', 'reject'].includes(action)) {
    throw new Error('INVALID_ACTION');
  }

  // 驳回时 reason 必填
  if (action === 'reject' && (!reason || reason.trim() === '')) {
    throw new Error('REASON_REQUIRED');
  }

  // Step 1: 查询商品，仅草稿状态可审核（幂等守卫）
  const rows = await db.query(
    'SELECT id, name, description, status FROM spu WHERE id = ? AND status = ?',
    [productId, 'draft']
  );

  if (!rows.length) {
    throw new Error('PRODUCT_NOT_FOUND');
  }

  const spu = rows[0];

  // Step 2: 敏感词过滤（仅通过时检测）
  let sensitiveWords = [];
  if (action === 'approve') {
    sensitiveWords = await filterSensitiveWords(spu.name, spu.description || '');
    if (sensitiveWords.length > 0) {
      const err = new Error('SENSITIVE_WORD');
      err.sensitiveWords = sensitiveWords;
      throw err;
    }
  }

  // Step 3-5: 事务 — UPDATE spu status + INSERT operation_log
  const conn = await db.beginTransaction();
  try {
    const newStatus = action === 'approve' ? 'listed' : 'draft';

    await conn.execute(
      'UPDATE spu SET status = ? WHERE id = ?',
      [newStatus, productId]
    );

    const detail = JSON.stringify({
      before: spu.status,
      after: newStatus,
      reason: reason || null,
      sensitiveWords: sensitiveWords.length > 0 ? sensitiveWords : null
    });

    await conn.execute(
      'INSERT INTO operation_logs (admin_id, action, target_type, target_id, detail) VALUES (?, ?, ?, ?, ?)',
      [adminId, 'review_product', 'product', productId, detail]
    );

    await db.commit(conn);

    return { productId, status: newStatus };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 敏感词过滤服务（双模式）
 * mock: 跳过检测，返回空
 * real: 调用第三方API，超时2s → 标记"机审跳过"
 * @param {string} name
 * @param {string} description
 * @returns {string[]} 敏感词列表
 */
async function filterSensitiveWords(name, description) {
  if (SENSITIVE_WORD_MODE === 'mock') {
    // mock: 模拟无敏感词
    return [];
  }

  // real: 调用敏感词过滤 API
  const SENSITIVE_WORD_API = process.env.SENSITIVE_WORD_API_URL;
  if (!SENSITIVE_WORD_API) {
    // 未配置 API 地址 → 跳过
    console.warn('[SENSITIVE_WORD] API URL not configured, skipping filter');
    return [];
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    const resp = await fetch(SENSITIVE_WORD_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: `${name} ${description}` }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!resp.ok) {
      console.warn('[SENSITIVE_WORD] API returned non-OK, skipping filter');
      return [];
    }

    const data = await resp.json();
    return data.words || [];
  } catch (e) {
    // 超时或网络错误 → 标记"机审跳过"
    console.warn('[SENSITIVE_WORD] API timeout/unavailable, skipping auto-filter');
    return [];
  }
}

module.exports = { listProducts, reviewProduct };

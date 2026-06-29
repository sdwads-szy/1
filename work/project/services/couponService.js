const db = require('../config/db');

/**
 * 列出所有可领取的优惠券（有效期内 + 状态为 active）
 * @returns {Array} 优惠券列表
 */
async function listAvailableCoupons() {
  const sql = `SELECT id, title, amount, min_order, valid_from, valid_to, status, created_at
    FROM coupons
    WHERE status = 'active'
      AND valid_from <= NOW()
      AND valid_to >= NOW()
    ORDER BY created_at DESC`;
  const rows = await db.query(sql);
  return rows;
}

/**
 * 用户领取优惠券（幂等：同一用户+同一券只领一次）
 * @param {number} userId
 * @param {number} couponId
 * @returns {{ userCouponId: number }}
 */
async function claimCoupon(userId, couponId) {
  // 1. 校验券是否存在且状态正常
  const coupons = await db.query('SELECT id, status, valid_from, valid_to FROM coupons WHERE id = ?', [couponId]);
  if (!coupons.length) {
    throw new Error('COUPON_NOT_FOUND');
  }
  const coupon = coupons[0];

  if (coupon.status !== 'active') {
    throw new Error('COUPON_EXPIRED');
  }

  // 2. 校验是否在有效期内
  const now = new Date();
  if (new Date(coupon.valid_from) > now || new Date(coupon.valid_to) < now) {
    throw new Error('COUPON_EXPIRED');
  }

  // 3. 幂等检查：是否已领取
  const existing = await db.query(
    'SELECT id FROM user_coupons WHERE user_id = ? AND coupon_id = ?',
    [userId, couponId]
  );
  if (existing.length) {
    throw new Error('ALREADY_CLAIMED');
  }

  // 4. 写入领取记录
  const result = await db.query(
    'INSERT INTO user_coupons (user_id, coupon_id, status) VALUES (?, ?, ?)',
    [userId, couponId, 'available']
  );

  return { userCouponId: result.insertId };
}

/**
 * 获取用户的可用优惠券列表
 * @param {number} userId
 * @param {number} [orderAmount] - 订单金额，用于过滤门槛
 * @returns {Array}
 */
async function getMyCoupons(userId, orderAmount) {
  let sql = `SELECT uc.id, uc.coupon_id, c.title, c.amount, c.min_order,
      c.valid_from, c.valid_to, uc.status, uc.created_at
    FROM user_coupons uc
    JOIN coupons c ON uc.coupon_id = c.id
    WHERE uc.user_id = ?
      AND uc.status = 'available'
      AND c.status = 'active'
      AND c.valid_from <= NOW()
      AND c.valid_to >= NOW()`;

  const params = [userId];

  // 按订单金额过滤门槛
  if (orderAmount !== undefined && orderAmount !== null && !Number.isNaN(orderAmount)) {
    sql += ' AND c.min_order <= ?';
    params.push(orderAmount);
  }

  sql += ' ORDER BY c.amount DESC, uc.created_at DESC';

  const rows = await db.query(sql, params);
  return rows;
}

/**
 * 管理员分页查询优惠券列表
 * @param {{ status?: string, page: number, pageSize: number }} filters
 * @returns {{ list: Array, total: number, page: number, pageSize: number }}
 */
async function listAdminCoupons(filters = {}) {
  const { status, page = 1, pageSize = 20 } = filters;

  let whereClause = 'WHERE 1=1';
  const params = [];

  if (status) {
    whereClause += ' AND status = ?';
    params.push(status);
  }

  // 计数
  const countSql = `SELECT COUNT(*) AS total FROM coupons ${whereClause}`;
  const countResult = await db.query(countSql, params);
  const total = countResult[0].total;

  // 分页查询
  const offset = (page - 1) * pageSize;
  const dataSql = `SELECT id, title, amount, min_order, valid_from, valid_to, status, created_at
    FROM coupons ${whereClause}
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?`;
  const list = await db.query(dataSql, [...params, pageSize, offset]);

  return { list, total, page, pageSize };
}

/**
 * 管理员创建优惠券
 * @param {{ title: string, amount: number, minOrder: number, validFrom: string, validTo: string }} data
 * @returns {{ couponId: number }}
 */
async function createCoupon(data) {
  const { title, amount, minOrder = 0, validFrom, validTo } = data;

  // 校验有效期：开始 < 结束
  if (new Date(validFrom) >= new Date(validTo)) {
    throw new Error('COUPON_INVALID_DATE');
  }

  const result = await db.query(
    'INSERT INTO coupons (title, amount, min_order, valid_from, valid_to) VALUES (?, ?, ?, ?, ?)',
    [title, amount, minOrder, validFrom, validTo]
  );

  return { couponId: result.insertId };
}

/**
 * 管理员发放优惠券
 * @param {number} couponId
 * @param {Array<number>|null} userIds - null 或空数组表示全场发放
 * @returns {{ grantedCount: number }}
 */
async function grantCoupon(couponId, userIds) {
  // 1. 校验券是否存在
  const coupons = await db.query('SELECT id FROM coupons WHERE id = ?', [couponId]);
  if (!coupons.length) {
    throw new Error('COUPON_NOT_FOUND');
  }

  // 2. 确定目标用户
  let targetUserIds;

  if (!userIds || !userIds.length) {
    // 全场发放：所有 active 用户
    const users = await db.query("SELECT id FROM users WHERE status = 'active'");
    targetUserIds = users.map(u => u.id);
  } else {
    // 定向发放：校验用户存在
    const users = await db.query(
      'SELECT id FROM users WHERE id IN (?) AND status = ?',
      [userIds, 'active']
    );
    targetUserIds = users.map(u => u.id);

    if (targetUserIds.length < userIds.length) {
      throw new Error('USERS_NOT_FOUND');
    }
  }

  if (!targetUserIds.length) {
    return { grantedCount: 0 };
  }

  // 3. 批量插入（IGNORE 跳过已领取的）
  const valuePlaceholders = targetUserIds.map(() => '(?, ?, ?)').join(', ');
  const flatParams = [];
  targetUserIds.forEach(uid => {
    flatParams.push(uid, couponId, 'available');
  });

  const result = await db.query(
    `INSERT IGNORE INTO user_coupons (user_id, coupon_id, status) VALUES ${valuePlaceholders}`,
    flatParams
  );

  return { grantedCount: result.affectedRows };
}

module.exports = {
  listAvailableCoupons,
  claimCoupon,
  getMyCoupons,
  listAdminCoupons,
  createCoupon,
  grantCoupon
};

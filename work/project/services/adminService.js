const db = require('../config/db');
const { decrypt } = require('../utils/encryption');

// ==================== 工具函数 ====================

/**
 * 脱敏手机号：138****1234
 */
function maskPhone(phone) {
  if (!phone || phone.length < 7) return phone || '***';
  return phone.slice(0, 3) + '****' + phone.slice(-4);
}

/**
 * 安全解密手机号，失败返回原始值
 */
function safeDecrypt(cipher) {
  try {
    return decrypt(cipher);
  } catch {
    return cipher;
  }
}

/**
 * 将数据库行中的 phone 解密并脱敏，created_at → createdAt
 */
function formatUserRow(row) {
  return {
    id: row.id,
    phone: maskPhone(safeDecrypt(row.phone)),
    nickname: row.nickname,
    avatar: row.avatar,
    role: row.role,
    status: row.status,
    createdAt: row.created_at,
  };
}

/**
 * 构建日期范围 WHERE 条件
 */
function buildDateRange(startDate, endDate, field = 'created_at') {
  const conditions = [];
  const params = [];
  if (startDate) {
    conditions.push(`${field} >= ?`);
    params.push(startDate);
  }
  if (endDate) {
    conditions.push(`${field} <= ?`);
    params.push(endDate + ' 23:59:59');
  }
  return { where: conditions.length ? 'WHERE ' + conditions.join(' AND ') : '', params };
}

// ==================== 用户管理 ====================

/**
 * 查询用户列表
 * @param {object} filters - { phone?, status?, role?, page?, pageSize? }
 * @returns {{ list, total, page, pageSize }}
 */
async function listUsers(filters) {
  const { phone, status, role, page: rawPage, pageSize: rawPageSize } = filters || {};
  const page = parseInt(rawPage) || 1;
  const pageSize = parseInt(rawPageSize) || 20;
  const offset = (page - 1) * pageSize;

  // 构建可走索引的条件
  const conditions = [];
  const params = [];
  if (status) {
    conditions.push('status = ?');
    params.push(status);
  }
  if (role) {
    conditions.push('role = ?');
    params.push(role);
  }
  const where = conditions.length ? 'WHERE ' + conditions.join(' AND ') : '';

  // phone 加密存储，无法走 SQL 过滤 → 查出全部后在应用层过滤
  if (phone) {
    const rows = await db.query(
      `SELECT id, phone, nickname, avatar, role, status, created_at FROM users ${where} ORDER BY id DESC`,
      params
    );
    // 解密后筛选
    const filtered = rows.filter(r => {
      const plain = safeDecrypt(r.phone);
      return plain.includes(phone);
    });
    const total = filtered.length;
    const paged = filtered.slice(offset, offset + pageSize);
    return {
      list: paged.map(formatUserRow),
      total,
      page,
      pageSize,
    };
  }

  // 无 phone 过滤 → SQL 分页
  const countRows = await db.query(
    `SELECT COUNT(*) as total FROM users ${where}`,
    params
  );
  const total = countRows[0].total;

  const rows = await db.query(
    `SELECT id, phone, nickname, avatar, role, status, created_at FROM users ${where} ORDER BY id DESC LIMIT ? OFFSET ?`,
    [...params, pageSize, offset]
  );

  return {
    list: rows.map(formatUserRow),
    total,
    page,
    pageSize,
  };
}

/**
 * 封禁用户
 * @param {number} adminId - 操作者 ID
 * @param {number} targetUserId - 目标用户 ID
 */
async function banUser(adminId, targetUserId) {
  // 查询目标用户
  const rows = await db.query('SELECT id, role, status FROM users WHERE id = ?', [targetUserId]);
  if (!rows.length) throw new Error('USER_NOT_FOUND');

  const target = rows[0];

  // 不能封禁自己
  if (targetUserId === adminId) throw new Error('CANNOT_BAN_SELF');

  // 不能封禁管理员
  if (target.role === 'admin') throw new Error('CANNOT_BAN_ADMIN');

  // 已是封禁状态，幂等返回
  if (target.status === 'banned') return { affectedRows: 0 };

  const result = await db.query('UPDATE users SET status = ? WHERE id = ?', ['banned', targetUserId]);
  return result;
}

/**
 * 解封用户
 * @param {number} targetUserId - 目标用户 ID
 */
async function unbanUser(targetUserId) {
  const rows = await db.query('SELECT id FROM users WHERE id = ?', [targetUserId]);
  if (!rows.length) throw new Error('USER_NOT_FOUND');

  const result = await db.query('UPDATE users SET status = ? WHERE id = ?', ['active', targetUserId]);
  return result;
}

/**
 * 分配角色
 * @param {number} adminId - 操作者 ID
 * @param {number} targetUserId - 目标用户 ID
 * @param {string} role - 新角色
 */
async function setUserRole(adminId, targetUserId, role) {
  const rows = await db.query('SELECT id FROM users WHERE id = ?', [targetUserId]);
  if (!rows.length) throw new Error('USER_NOT_FOUND');

  const result = await db.query('UPDATE users SET role = ? WHERE id = ?', [role, targetUserId]);
  return result;
}

// ==================== 经营报表 ====================

/**
 * 订单报表
 * @returns {{ totalOrders, totalAmount, byStatus, byDate }}
 */
async function getOrderReport(startDate, endDate) {
  const { where, params } = buildDateRange(startDate, endDate, 'created_at');

  // 总计
  const summaryRows = await db.query(
    `SELECT COUNT(*) as totalOrders, COALESCE(SUM(pay_amount), 0) as totalAmount
     FROM orders ${where}`,
    params
  );
  const { totalOrders, totalAmount } = summaryRows[0];

  // 按状态分组
  const statusRows = await db.query(
    `SELECT status, COUNT(*) as count, COALESCE(SUM(pay_amount), 0) as amount
     FROM orders ${where} GROUP BY status`,
    params
  );
  const byStatus = statusRows.map(r => ({
    status: r.status,
    count: r.count,
    amount: String(r.amount),
  }));

  // 按日期分组
  const dateRows = await db.query(
    `SELECT DATE(created_at) as date, COUNT(*) as count, COALESCE(SUM(pay_amount), 0) as amount
     FROM orders ${where} GROUP BY DATE(created_at) ORDER BY date`,
    params
  );
  const byDate = dateRows.map(r => ({
    date: r.date,
    count: r.count,
    amount: String(r.amount),
  }));

  return {
    totalOrders,
    totalAmount: String(totalAmount),
    byStatus,
    byDate,
  };
}

/**
 * 支付报表
 * @returns {{ totalPayments, totalAmount, byChannel }}
 */
async function getPaymentReport(startDate, endDate) {
  const { where, params } = buildDateRange(startDate, endDate, 'created_at');

  // 总计（仅统计已支付）
  const summaryRows = await db.query(
    `SELECT COUNT(*) as totalPayments, COALESCE(SUM(amount), 0) as totalAmount
     FROM payments ${where ? where + ' AND status = \'paid\'' : 'WHERE status = \'paid\''}`,
    params
  );
  const { totalPayments, totalAmount } = summaryRows[0];

  // 按渠道分组
  const channelRows = await db.query(
    `SELECT channel, COUNT(*) as count, COALESCE(SUM(amount), 0) as amount
     FROM payments ${where ? where + ' AND status = \'paid\'' : 'WHERE status = \'paid\''}
     GROUP BY channel`,
    params
  );
  const byChannel = channelRows.map(r => ({
    channel: r.channel,
    count: r.count,
    amount: String(r.amount),
  }));

  return {
    totalPayments,
    totalAmount: String(totalAmount),
    byChannel,
  };
}

/**
 * 退款报表
 * @returns {{ totalRefunds, totalAmount, refundRate }}
 */
async function getRefundReport(startDate, endDate) {
  const { where, params } = buildDateRange(startDate, endDate, 'created_at');

  // 退款汇总（已完成的退款）
  const refundRows = await db.query(
    `SELECT COUNT(*) as totalRefunds, COALESCE(SUM(amount), 0) as totalAmount
     FROM refunds ${where ? where + ' AND status = \'completed\'' : 'WHERE status = \'completed\''}`,
    params
  );
  const { totalRefunds, totalAmount } = refundRows[0];

  // 同期支付总额（用于计算退款率）
  const payRows = await db.query(
    `SELECT COALESCE(SUM(amount), 0) as totalPayAmount
     FROM payments ${where ? where + ' AND status = \'paid\'' : 'WHERE status = \'paid\''}`,
    params
  );
  const totalPayAmount = payRows[0].totalPayAmount;

  const refundRate = totalPayAmount > 0
    ? (parseFloat(totalAmount) / parseFloat(totalPayAmount) * 100).toFixed(2) + '%'
    : '0.00%';

  return {
    totalRefunds,
    totalAmount: String(totalAmount),
    refundRate,
  };
}

module.exports = {
  listUsers,
  banUser,
  unbanUser,
  setUserRole,
  getOrderReport,
  getPaymentReport,
  getRefundReport,
};

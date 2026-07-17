const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const db = require('../config/db');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-key';
const ACCESS_TOKEN_EXPIRY = '15m';
const REFRESH_TOKEN_EXPIRY_DAYS = 7;
const SMS_MODE = process.env.SMS_MODE || 'mock';

// ═══════════════════════════════════════════
// 私有工具函数
// ═══════════════════════════════════════════

/** 签发 access_token（JWT，15min有效） */
function signAccessToken(user) {
  return jwt.sign(
    { userId: user.id, role: user.role },
    JWT_SECRET,
    { expiresIn: ACCESS_TOKEN_EXPIRY }
  );
}

/** 生成 refresh_token（随机 32 字节 hex 字符串） */
function generateRefreshToken() {
  return crypto.randomBytes(32).toString('hex');
}

/** 对 refresh_token 做 SHA256 哈希，存入数据库 */
function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

// ═══════════════════════════════════════════
// DB-API 层（与契约 db_api_* 一一对应）
// ═══════════════════════════════════════════

/** db_api_get_user_by_mobile — 按手机号查用户 */
async function getUserByMobile(mobile) {
  const rows = await db.query(
    'SELECT id, mobile, password_hash, nickname, avatar, role, status FROM users WHERE mobile = ?',
    [mobile]
  );
  return rows.length ? rows[0] : null;
}

/** db_api_create_user — 创建用户 */
async function createUser(mobile, passwordHash, nickname, role) {
  const result = await db.query(
    'INSERT INTO users (mobile, password_hash, nickname, role) VALUES (?, ?, ?, ?)',
    [mobile, passwordHash, nickname, role]
  );
  return { id: result.insertId, mobile, nickname, role };
}

/** db_api_get_user_by_id — 按主键查用户 */
async function getUserById(userId) {
  const rows = await db.query(
    'SELECT id, mobile, nickname, avatar, role, status, created_at FROM users WHERE id = ?',
    [userId]
  );
  if (!rows.length) throw new Error('USER_NOT_FOUND');
  return rows[0];
}

/** db_api_create_refresh_token — 写入 refresh_token 哈希 */
async function createRefreshTokenRecord(userId, tokenHash, expiresAt) {
  await db.query(
    'INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)',
    [userId, tokenHash, expiresAt]
  );
}

/** db_api_get_token_by_hash — 按哈希查有效 refresh_token */
async function getTokenByHash(tokenHash) {
  const rows = await db.query(
    'SELECT id, user_id, expires_at FROM refresh_tokens WHERE token_hash = ? AND expires_at > NOW()',
    [tokenHash]
  );
  return rows.length ? rows[0] : null;
}

/** db_api_delete_token — 删除 refresh_token（轮换用） */
async function deleteToken(tokenHash) {
  await db.query(
    'DELETE FROM refresh_tokens WHERE token_hash = ?',
    [tokenHash]
  );
}

// ═══════════════════════════════════════════
// SMS 验证码（双模式：mock / real）
// ═══════════════════════════════════════════

/** 校验短信验证码 */
function validateSmsCode(mobile, code) {
  if (SMS_MODE === 'mock') {
    // mock 模式：固定验证码 123456
    if (code === '123456') return;
    throw new Error('INVALID_CODE');
  }
  // real 模式：应查询 Redis 中的验证码并比对
  // 此处 real 实现需对接短信服务商
  throw new Error('CODE_EXPIRED');
}

// ═══════════════════════════════════════════
// 对外 Service 函数
// ═══════════════════════════════════════════

/**
 * 登录
 * @param {string} mobile - 手机号（11位，1开头）
 * @param {string} password - 明文密码
 * @returns {{ token, refreshToken, user: {userId, mobile, nickname, avatar, role} }}
 */
async function login(mobile, password) {
  // 1. 输入校验
  if (!mobile || !/^1[3-9]\d{9}$/.test(mobile)) {
    throw new Error('INVALID_MOBILE');
  }
  if (!password || password.length < 6) {
    throw new Error('INVALID_PASSWORD');
  }

  // 2. 查用户
  const user = await getUserByMobile(mobile);
  if (!user) {
    throw new Error('PHONE_NOT_FOUND');
  }

  // 3. 检查账号状态
  if (user.status === 'disabled') {
    throw new Error('ACCOUNT_DISABLED');
  }

  // 4. 验密
  const valid = await bcrypt.compare(password, user.password_hash);
  if (!valid) {
    throw new Error('PASSWORD_WRONG');
  }

  // 5. 签发 token 对
  const accessToken = signAccessToken(user);
  const refreshToken = generateRefreshToken();
  const refreshHash = hashToken(refreshToken);
  const expiresAt = new Date(Date.now() + REFRESH_TOKEN_EXPIRY_DAYS * 24 * 60 * 60 * 1000);

  await createRefreshTokenRecord(user.id, refreshHash, expiresAt);

  return {
    token: accessToken,
    refreshToken,
    user: {
      userId: user.id,
      mobile: user.mobile,
      nickname: user.nickname,
      avatar: user.avatar,
      role: user.role
    }
  };
}

/**
 * 注册
 * @param {string} mobile - 手机号
 * @param {string} code - 短信验证码（6位数字）
 * @param {string} password - 明文密码（≥8位含数字+字母）
 * @returns {{ token, refreshToken, user: {userId, mobile, nickname, avatar, role} }}
 */
async function register(mobile, code, password) {
  // 1. 输入校验
  if (!mobile || !/^1[3-9]\d{9}$/.test(mobile)) {
    throw new Error('INVALID_MOBILE');
  }
  if (!code || !/^\d{6}$/.test(code)) {
    throw new Error('INVALID_CODE');
  }
  if (!password || password.length < 8 || !/\d/.test(password) || !/[a-zA-Z]/.test(password)) {
    throw new Error('WEAK_PASSWORD');
  }

  // 2. 手机号唯一性检查
  const existing = await getUserByMobile(mobile);
  if (existing) {
    throw new Error('PHONE_EXISTS');
  }

  // 3. 验证短信验证码
  validateSmsCode(mobile, code);

  // 4. 密码哈希
  const passwordHash = await bcrypt.hash(password, 10);

  // 5. 创建用户（昵称默认 '用户'+手机尾号）
  const nickname = '用户' + mobile.slice(-4);
  const newUser = await createUser(mobile, passwordHash, nickname, 'user');

  // 6. 签发 token 对
  const accessToken = jwt.sign(
    { userId: newUser.id, role: newUser.role },
    JWT_SECRET,
    { expiresIn: ACCESS_TOKEN_EXPIRY }
  );
  const refreshToken = generateRefreshToken();
  const refreshHash = hashToken(refreshToken);
  const expiresAt = new Date(Date.now() + REFRESH_TOKEN_EXPIRY_DAYS * 24 * 60 * 60 * 1000);

  await createRefreshTokenRecord(newUser.id, refreshHash, expiresAt);

  return {
    token: accessToken,
    refreshToken,
    user: {
      userId: newUser.id,
      mobile: newUser.mobile,
      nickname: newUser.nickname,
      avatar: null,
      role: newUser.role
    }
  };
}

/**
 * 刷新 Token（轮换策略）
 * 1. 哈希旧 refreshToken 查库 → 不存在/过期 → 401
 * 2. 删除旧记录
 * 3. 查用户信息 → 签发新 token 对
 * @param {string} oldRefreshToken - 客户端传来的 refresh token 原文
 * @returns {{ token, refreshToken, user: {userId, mobile, nickname, avatar, role} }}
 */
async function refreshToken(oldRefreshToken) {
  // 1. 空值校验
  if (!oldRefreshToken) {
    throw new Error('REFRESH_TOKEN_INVALID');
  }

  // 2. 查库
  const oldHash = hashToken(oldRefreshToken);
  const tokenRecord = await getTokenByHash(oldHash);

  if (!tokenRecord) {
    throw new Error('REFRESH_TOKEN_INVALID');
  }

  // 3. 过期检查（getTokenByHash 已用 expires_at > NOW() 过滤，此处兜底）
  if (new Date(tokenRecord.expires_at) < new Date()) {
    await deleteToken(oldHash);
    throw new Error('REFRESH_TOKEN_EXPIRED');
  }

  // 4. 删除旧 token（轮换）
  await deleteToken(oldHash);

  // 5. 查用户
  const user = await getUserById(tokenRecord.user_id);

  if (user.status === 'disabled') {
    throw new Error('ACCOUNT_DISABLED');
  }

  // 6. 签发新 token 对
  const accessToken = signAccessToken(user);
  const newRefreshToken = generateRefreshToken();
  const newRefreshHash = hashToken(newRefreshToken);
  const expiresAt = new Date(Date.now() + REFRESH_TOKEN_EXPIRY_DAYS * 24 * 60 * 60 * 1000);

  await createRefreshTokenRecord(user.id, newRefreshHash, expiresAt);

  return {
    token: accessToken,
    refreshToken: newRefreshToken,
    user: {
      userId: user.id,
      mobile: user.mobile,
      nickname: user.nickname,
      avatar: user.avatar,
      role: user.role
    }
  };
}

module.exports = { login, register, refreshToken };

const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const db = require('../config/db');
const redis = require('../config/redis');
const logger = require('../config/logger');
const { encrypt } = require('../utils/encryption');

const JWT_SECRET = process.env.JWT_SECRET;
const JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET;
const JWT_EXPIRES_IN = parseInt(process.env.JWT_EXPIRES_IN) || 3600;
const REFRESH_EXPIRES_IN = 86400;

const SMS_CODE_TTL = 60;
const SMS_RATE_LIMIT = 5;
const SMS_RATE_WINDOW = 86400;

/**
 * 发送短信验证码，含频率限制（每手机号每天最多5次）
 * @param {string} phone - 手机号
 * @returns {{ success: boolean, expireIn: number }}
 */
async function sendVerifyCode(phone) {
  if (!phone || !/^1[3-9]\d{9}$/.test(phone)) {
    throw new Error('INVALID_PHONE');
  }

  const rateKey = `sms_rate:${phone}`;
  const count = parseInt(await redis.get(rateKey)) || 0;
  if (count >= SMS_RATE_LIMIT) {
    throw new Error('RATE_LIMITED');
  }

  const code = String(Math.floor(100000 + Math.random() * 900000));

  const codeKey = `sms_code:${phone}`;
  await redis.set(codeKey, code);
  await redis.expire(codeKey, SMS_CODE_TTL);

  await redis.incr(rateKey);
  await redis.expire(rateKey, SMS_RATE_WINDOW);

  logger.info(`[SMS] Code sent to ${phone}: ${code}`);

  return { success: true, expireIn: SMS_CODE_TTL };
}

/**
 * 校验Redis中存储的短信验证码，验证后删除
 * @param {string} phone
 * @param {string} code
 */
async function verifySmsCode(phone, code) {
  const codeKey = `sms_code:${phone}`;
  const storedCode = await redis.get(codeKey);

  if (!storedCode) {
    throw new Error('VERIFY_CODE_EXPIRED');
  }

  if (storedCode !== code) {
    throw new Error('VERIFY_CODE_WRONG');
  }

  await redis.del(codeKey);
}

/**
 * 手机号+验证码登录（首次自动注册）
 * @param {string} phone
 * @param {string} verifyCode
 * @returns {{ userId, token, refreshToken, role, isNewUser }}
 */
async function loginByPhone(phone, verifyCode) {
  await verifySmsCode(phone, verifyCode);

  const encryptedPhone = encrypt(phone);
  const rows = await db.query(
    'SELECT id, phone, nickname, avatar, role, status FROM users WHERE phone = ?',
    [encryptedPhone]
  );

  let user;
  let isNewUser = false;

  if (rows.length === 0) {
    const randomPassword = generateRandomPassword();
    const hashedPassword = await bcrypt.hash(randomPassword, 10);
    const defaultNickname = `用户${phone.slice(-4)}`;

    const result = await db.query(
      'INSERT INTO users (phone, password, nickname, role, status) VALUES (?, ?, ?, ?, ?)',
      [encryptedPhone, hashedPassword, defaultNickname, 'user', 'active']
    );

    user = {
      id: result.insertId,
      phone,
      nickname: defaultNickname,
      avatar: '',
      role: 'user',
      status: 'active'
    };
    isNewUser = true;
  } else {
    user = rows[0];
    if (user.status === 'banned') {
      throw new Error('USER_BANNED');
    }
    user.phone = phone;
  }

  const tokens = generateTokenPair(user.id, user.role);

  return {
    userId: user.id,
    token: tokens.token,
    refreshToken: tokens.refreshToken,
    role: user.role,
    isNewUser
  };
}

/**
 * 微信OAuth登录（占位，实际需对接微信开放平台）
 * @param {string} oauthCode
 */
async function loginByOAuth(oauthCode) {
  if (!oauthCode) {
    throw new Error('OAUTH_FAIL');
  }
  throw new Error('OAUTH_FAIL');
}

/**
 * 刷新双Token：校验refreshToken → 签发新Token对
 * @param {string} refreshToken
 * @returns {{ token: string, refreshToken: string }}
 */
async function refreshTokens(refreshToken) {
  let decoded;
  try {
    decoded = jwt.verify(refreshToken, JWT_REFRESH_SECRET);
  } catch (e) {
    throw new Error('INVALID_REFRESH_TOKEN');
  }

  if (decoded.type !== 'refresh') {
    throw new Error('INVALID_REFRESH_TOKEN');
  }

  const rows = await db.query(
    'SELECT id, status FROM users WHERE id = ?',
    [decoded.userId]
  );

  if (rows.length === 0) {
    throw new Error('USER_NOT_FOUND');
  }

  if (rows[0].status === 'banned') {
    throw new Error('USER_BANNED');
  }

  return generateTokenPair(decoded.userId, decoded.role);
}

/**
 * 登出
 * @param {number} userId
 * @returns {{ success: boolean }}
 */
async function logout(userId) {
  logger.info(`[auth] User ${userId} logged out`);
  return { success: true };
}

/**
 * 签发 JWT 双Token
 * @param {number} userId
 * @param {string} role
 * @returns {{ token: string, refreshToken: string }}
 */
function generateTokenPair(userId, role) {
  const payload = { userId, role };
  const token = jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
  const refreshToken = jwt.sign(
    { userId, role, type: 'refresh' },
    JWT_REFRESH_SECRET,
    { expiresIn: REFRESH_EXPIRES_IN }
  );
  return { token, refreshToken };
}

/**
 * 生成随机密码（首次注册时自动生成，用户后续可自行修改）
 * @returns {string}
 */
function generateRandomPassword() {
  const chars = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678';
  let password = '';
  for (let i = 0; i < 16; i++) {
    password += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return password;
}

module.exports = {
  sendVerifyCode,
  loginByPhone,
  loginByOAuth,
  refreshTokens,
  logout
};

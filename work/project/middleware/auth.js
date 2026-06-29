const jwt = require('jsonwebtoken');
const response = require('../utils/response');

/**
 * 从请求头提取 Bearer Token
 * @param {import('express').Request} req
 * @returns {string|null}
 */
function extractToken(req) {
  const header = req.headers.authorization;
  if (!header) return null;
  const parts = header.split(' ');
  if (parts.length !== 2 || parts[0] !== 'Bearer') return null;
  return parts[1];
}

/**
 * JWT 认证中间件 — 必须提供有效 token，否则返回 401
 * 注入 req.userId（int）和 req.user（{ userId, role, iat, exp }）
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} next
 */
async function authenticate(req, res, next) {
  try {
    const token = extractToken(req);
    if (!token) {
      return response.unauthorized(res, '缺少认证令牌');
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    req.userId = decoded.userId;
    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return response.unauthorized(res, '令牌已过期，请重新登录');
    }
    if (err.name === 'JsonWebTokenError') {
      return response.unauthorized(res, '无效的认证令牌');
    }
    return response.error(res, '认证服务异常');
  }
}

/**
 * 可选认证中间件 — token 存在且有效时注入用户信息，不存在或无效时不报错
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} next
 */
async function optionalAuth(req, res, next) {
  try {
    const token = extractToken(req);
    if (!token) return next();

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    req.userId = decoded.userId;
  } catch {
    // token 无效时静默跳过，不阻断请求
  }
  next();
}

module.exports = { authenticate, optionalAuth };

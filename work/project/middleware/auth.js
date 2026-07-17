const jwt = require('jsonwebtoken');
const response = require('../utils/response');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-key-change-in-production';

/**
 * JWT 认证中间件
 * 从 Authorization: Bearer <token> 提取并验证 JWT，
 * 成功后注入 req.userId (int) 和 req.user ({userId, role, iat, exp})
 * 失败返回 401
 */
async function authenticate(req, res, next) {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return response.unauthorized(res, '请先登录');
    }

    const token = authHeader.split(' ')[1];
    const decoded = jwt.verify(token, JWT_SECRET);

    req.user = decoded;
    req.userId = decoded.userId;

    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return response.unauthorized(res, '令牌已过期，请重新登录');
    }
    if (err.name === 'JsonWebTokenError') {
      return response.unauthorized(res, '无效的令牌');
    }
    if (err.name === 'NotBeforeError') {
      return response.unauthorized(res, '令牌尚未生效');
    }
    return response.unauthorized(res, '认证失败');
  }
}

/**
 * 可选认证中间件
 * 有合法 token 时注入 req.userId / req.user，无 token 或 token 无效时 req.userId = null 继续
 */
async function optionalAuth(req, res, next) {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      req.userId = null;
      req.user = null;
      return next();
    }

    const token = authHeader.split(' ')[1];
    const decoded = jwt.verify(token, JWT_SECRET);

    req.user = decoded;
    req.userId = decoded.userId;

    next();
  } catch (err) {
    req.userId = null;
    req.user = null;
    next();
  }
}

/**
 * 角色要求中间件
 * 用户角色必须在允许列表中，通常在 authenticate 之后使用
 * @param  {...string} roles 允许的角色
 * @returns {Function} Express 中间件
 */
function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return response.unauthorized(res, '请先登录');
    }
    if (!roles.includes(req.user.role)) {
      return response.forbidden(res, '无权访问，角色不足');
    }
    next();
  };
}

module.exports = { authenticate, optionalAuth, requireRole };

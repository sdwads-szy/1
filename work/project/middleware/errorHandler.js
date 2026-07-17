const logger = require('../config/logger');
const response = require('../utils/response');

/**
 * 自定义应用错误类
 * 业务逻辑中抛出 → errorHandler 捕获 → 返回统一格式错误响应
 */
class AppError extends Error {
  /**
   * @param {string}  message    错误消息（用户可见）
   * @param {number}  statusCode HTTP 状态码（默认 500）
   * @param {string}  code       业务错误码（如 'INSUFFICIENT_STOCK'）
   */
  constructor(message, statusCode = 500, code = 'INTERNAL_ERROR') {
    super(message);
    this.name = 'AppError';
    this.statusCode = statusCode;
    this.code = code;
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * 全局错误处理中间件（4 参数签名）
 * 捕获所有 throw / next(err) 传播的错误，记录日志并返回统一格式响应
 */
function errorHandler(err, req, res, _next) {
  // 记录完整错误上下文
  logger.error(err.message, {
    name: err.name,
    code: err.code,
    statusCode: err.statusCode,
    stack: err.stack,
    url: req.originalUrl,
    method: req.method,
    userId: req.userId || null
  });

  // 已知应用错误 → 直接返回
  if (err instanceof AppError) {
    return response.fail(res, err.message, err.statusCode, null);
  }

  // JWT 相关错误（可能在路由层之外被抛出）
  if (err.name === 'TokenExpiredError') {
    return response.unauthorized(res, '令牌已过期，请重新登录');
  }
  if (err.name === 'JsonWebTokenError') {
    return response.unauthorized(res, '无效的令牌');
  }
  if (err.name === 'NotBeforeError') {
    return response.unauthorized(res, '令牌尚未生效');
  }

  // 生产环境隐藏内部错误细节
  if (process.env.NODE_ENV === 'production') {
    return response.error(res, '服务器内部错误');
  }

  // 开发环境返回原始错误信息便于调试
  return response.fail(res, err.message || '服务器内部错误', 500, null);
}

module.exports = { errorHandler, AppError };

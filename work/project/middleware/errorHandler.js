const logger = require('../config/logger');
const response = require('../utils/response');

/**
 * 应用层错误类 — 携带 HTTP 状态码和错误标识
 */
class AppError extends Error {
  /**
   * @param {string} message 错误消息
   * @param {number} statusCode HTTP 状态码，默认 400
   * @param {string} [code] 业务错误码
   */
  constructor(message, statusCode = 400, code) {
    super(message);
    this.name = 'AppError';
    this.statusCode = statusCode;
    this.code = code || 'APP_ERROR';
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * 全局错误处理中间件
 * @param {Error} err
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} _next
 */
function errorHandler(err, req, res, _next) {
  // 记录完整错误信息
  logger.error(`[${err.name}] ${err.message}`, {
    stack: err.stack,
    url: req.originalUrl,
    method: req.method,
    ip: req.ip,
    userId: req.userId || null,
  });

  // 已知的业务错误
  if (err instanceof AppError) {
    return response.fail(res, err.message, err.statusCode);
  }

  // JWT 相关错误（由其他中间件传播）
  if (err.name === 'TokenExpiredError') {
    return response.unauthorized(res, '令牌已过期，请重新登录');
  }
  if (err.name === 'JsonWebTokenError') {
    return response.unauthorized(res, '无效的认证令牌');
  }
  if (err.name === 'NotBeforeError') {
    return response.unauthorized(res, '令牌尚未生效');
  }

  // JSON 解析错误
  if (err.type === 'entity.parse.failed') {
    return response.fail(res, '请求体格式错误，请检查 JSON 结构', 400);
  }

  // 请求体过大
  if (err.type === 'entity.too.large') {
    return response.fail(res, '请求体过大', 413);
  }

  // URL 参数解析错误
  if (err instanceof URIError) {
    return response.fail(res, '请求 URL 包含非法字符', 400);
  }

  // 未知错误统一返回 500
  return response.error(res, '服务器内部错误');
}

module.exports = { errorHandler, AppError };

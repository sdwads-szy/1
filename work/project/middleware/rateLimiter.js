/**
 * 简易内存请求限流中间件
 * 基于滑动窗口算法，按 IP 维度限制请求频率
 */

const store = new Map();

// 定期清理过期条目，防止内存泄漏
const CLEANUP_INTERVAL = 60 * 1000;
setInterval(() => {
  const now = Date.now();
  for (const [key, entry] of store) {
    if (now - entry.resetTime > 0) {
      store.delete(key);
    }
  }
}, CLEANUP_INTERVAL).unref();

/**
 * 创建限流中间件
 * @param {Object} options
 * @param {number} [options.windowMs=60000] 时间窗口（毫秒）
 * @param {number} [options.max=100] 窗口内最大请求数
 * @param {string} [options.message='请求过于频繁，请稍后再试'] 超限提示
 * @returns {import('express').RequestHandler}
 */
function createRateLimiter(options = {}) {
  const {
    windowMs = 60 * 1000,
    max = 100,
    message = '请求过于频繁，请稍后再试',
  } = options;

  return (req, res, next) => {
    const key = req.ip || req.connection.remoteAddress || 'unknown';
    const now = Date.now();

    let entry = store.get(key);

    if (!entry || now > entry.resetTime) {
      entry = { count: 0, resetTime: now + windowMs };
      store.set(key, entry);
    }

    entry.count++;

    // 设置限流相关响应头
    res.set('X-RateLimit-Limit', String(max));
    res.set('X-RateLimit-Remaining', String(Math.max(0, max - entry.count)));
    res.set('X-RateLimit-Reset', String(Math.ceil(entry.resetTime / 1000)));

    if (entry.count > max) {
      return res.status(429).json({
        success: false,
        code: 429,
        message,
        data: null,
      });
    }

    next();
  };
}

module.exports = { createRateLimiter };

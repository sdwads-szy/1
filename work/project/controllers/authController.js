const response = require('../utils/response');
const authService = require('../services/authService');

// ── 简易内存限流（1分钟窗口 / 最多5次 / 按IP区分）──
const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW = 60 * 1000;
const RATE_LIMIT_MAX = 5;

function checkRateLimit(ip) {
  const now = Date.now();
  const record = rateLimitMap.get(ip);

  if (!record || now - record.windowStart > RATE_LIMIT_WINDOW) {
    rateLimitMap.set(ip, { count: 1, windowStart: now });
    return true;
  }

  if (record.count >= RATE_LIMIT_MAX) {
    return false;
  }

  record.count++;
  return true;
}

// ── Cookie 配置 ──
const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'strict',
  maxAge: 7 * 24 * 60 * 60 * 1000, // 7天
  path: '/'
};

// ── 错误码 → HTTP 状态 + 消息 ──
const ERROR_MAP = {
  PHONE_NOT_FOUND:        { status: 404, message: '手机号未注册' },
  PASSWORD_WRONG:         { status: 401, message: '密码错误' },
  ACCOUNT_DISABLED:       { status: 403, message: '账号已被禁用' },
  PHONE_EXISTS:           { status: 409, message: '手机号已注册' },
  INVALID_CODE:           { status: 400, message: '验证码无效' },
  CODE_EXPIRED:           { status: 400, message: '验证码已过期' },
  WEAK_PASSWORD:          { status: 422, message: '密码强度不足，至少8位含数字和字母' },
  INVALID_MOBILE:         { status: 400, message: '手机号格式不正确' },
  INVALID_PASSWORD:       { status: 400, message: '密码格式不正确' },
  CODE_RATE_LIMIT:        { status: 429, message: '验证码发送过于频繁，请60秒后再试' },
  REFRESH_TOKEN_EXPIRED:  { status: 401, message: '登录已过期，请重新登录' },
  REFRESH_TOKEN_INVALID:  { status: 401, message: '无效的刷新令牌' },
  USER_NOT_FOUND:         { status: 404, message: '用户不存在' }
};

// ── POST /api/auth/login ──
/**
 * 用户登录：手机号+密码 → accessToken + refreshToken + user
 */
async function login(req, res) {
  try {
    if (!checkRateLimit(req.ip)) {
      return response.fail(res, '请求过于频繁，请稍后再试', 429);
    }

    const { mobile, password } = req.body;
    const result = await authService.login(mobile, password);

    res.cookie('refreshToken', result.refreshToken, COOKIE_OPTIONS);

    return response.success(res, {
      token: result.token,
      user: result.user
    });
  } catch (e) {
    const err = ERROR_MAP[e.message] || { status: 500, message: '服务器内部错误' };
    return response.fail(res, err.message, err.status);
  }
}

// ── POST /api/auth/register ──
/**
 * 用户注册：手机号+验证码+密码 → accessToken + refreshToken + user
 */
async function register(req, res) {
  try {
    if (!checkRateLimit(req.ip)) {
      return response.fail(res, '请求过于频繁，请稍后再试', 429);
    }

    const { mobile, code, password, nickname } = req.body;
    const result = await authService.register(mobile, code, password, nickname);

    res.cookie('refreshToken', result.refreshToken, COOKIE_OPTIONS);

    return response.success(res, {
      token: result.token,
      user: result.user
    });
  } catch (e) {
    const err = ERROR_MAP[e.message] || { status: 500, message: '服务器内部错误' };
    return response.fail(res, err.message, err.status);
  }
}

// ── POST /api/auth/refresh ──
/**
 * 刷新Token：用 HttpOnly Cookie 中的 refreshToken 换取新 accessToken
 * Token 轮换策略：旧 refreshToken 立即删除，签发新对
 */
async function refresh(req, res) {
  try {
    if (!checkRateLimit(req.ip)) {
      return response.fail(res, '请求过于频繁，请稍后再试', 429);
    }

    const refreshToken = req.cookies?.refreshToken || req.body?.refreshToken;
    const result = await authService.refreshToken(refreshToken);

    res.cookie('refreshToken', result.refreshToken, COOKIE_OPTIONS);

    return response.success(res, {
      token: result.token,
      user: result.user
    });
  } catch (e) {
    const err = ERROR_MAP[e.message] || { status: 500, message: '服务器内部错误' };
    return response.fail(res, err.message, err.status);
  }
}

module.exports = { login, register, refresh };

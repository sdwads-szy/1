const authService = require('../services/authService');
const response = require('../utils/response');
const logger = require('../config/logger');

/**
 * 登录：支持手机号+验证码 / 微信OAuth
 * POST /api/auth/login
 */
async function login(req, res) {
  try {
    const { phone, verifyCode, oauthCode } = req.body;

    let result;
    if (oauthCode) {
      result = await authService.loginByOAuth(oauthCode);
    } else {
      if (!phone || !verifyCode) {
        return response.fail(res, '手机号和验证码不能为空', 400);
      }
      result = await authService.loginByPhone(phone, verifyCode);
    }

    response.success(res, result, '登录成功');
  } catch (e) {
    handleAuthError(res, e);
  }
}

/**
 * 发送短信验证码
 * POST /api/auth/send-code
 */
async function sendCode(req, res) {
  try {
    const { phone } = req.body;
    if (!phone) {
      return response.fail(res, '手机号不能为空', 400);
    }

    const result = await authService.sendVerifyCode(phone);
    response.success(res, result, '验证码已发送');
  } catch (e) {
    handleAuthError(res, e);
  }
}

/**
 * 刷新Token
 * POST /api/auth/refresh
 */
async function refresh(req, res) {
  try {
    const { refreshToken } = req.body;
    if (!refreshToken) {
      return response.fail(res, '缺少刷新令牌', 400);
    }

    const result = await authService.refreshTokens(refreshToken);
    response.success(res, result, 'Token已刷新');
  } catch (e) {
    handleAuthError(res, e);
  }
}

/**
 * 登出
 * POST /api/auth/logout
 */
async function logout(req, res) {
  try {
    const result = await authService.logout(req.userId);
    response.success(res, result, '已登出');
  } catch (e) {
    handleAuthError(res, e);
  }
}

/**
 * 统一认证错误映射
 */
function handleAuthError(res, e) {
  const message = e.message || '';

  const errorMap = {
    'VERIFY_CODE_EXPIRED':  { status: 400, message: '验证码已过期' },
    'VERIFY_CODE_WRONG':    { status: 400, message: '验证码错误' },
    'RATE_LIMITED':          { status: 429, message: '请求过于频繁，请稍后再试' },
    'OAUTH_FAIL':            { status: 400, message: '微信授权失败' },
    'INVALID_PHONE':         { status: 400, message: '手机号格式不正确' },
    'USER_BANNED':           { status: 403, message: '账号已被封禁' },
    'INVALID_REFRESH_TOKEN': { status: 401, message: '刷新令牌无效' },
    'USER_NOT_FOUND':        { status: 404, message: '用户不存在' }
  };

  const mapping = errorMap[message];
  if (mapping) {
    return response.fail(res, mapping.message, mapping.status);
  }

  logger.error(`[auth] Unhandled error: ${message}`, e);
  response.fail(res, '服务器内部错误', 500);
}

module.exports = { login, sendCode, refresh, logout };

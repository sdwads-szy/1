/**
 * @api 认证模块 — 登录/注册/刷新Token/发送验证码/登出
 */
import request from '@/utils/request';

/**
 * 登录（手机号+验证码 或 OAuth授权码）
 * @param {Object} data - { phone, verifyCode } 或 { oauthCode }
 * @returns {Promise} { token, refreshToken, userId, role, isNewUser }
 */
export function login(data) {
  return request({ url: '/auth/login', method: 'post', data });
}

/**
 * 发送短信验证码
 * @param {Object} data - { phone }
 * @returns {Promise} { success, expireIn }
 */
export function sendCode(data) {
  return request({ url: '/auth/send-code', method: 'post', data });
}

/**
 * 刷新Token（拦截器自动调用）
 * @param {Object} data - { refreshToken }
 * @returns {Promise} { token, refreshToken }
 */
export function refresh(data) {
  return request({ url: '/auth/refresh', method: 'post', data });
}

/**
 * 登出
 * @returns {Promise} { success }
 */
export function logout() {
  return request({ url: '/auth/logout', method: 'post' });
}

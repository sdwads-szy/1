import request from '@/utils/request';

/**
 * 用户登录：手机号+密码
 * @param {Object} data - { mobile, password }
 * @returns {Promise} { token, refreshToken, user }
 */
export function login(data) {
  return request({ url: '/auth/login', method: 'post', data });
}

/**
 * 用户注册：手机号+验证码+密码
 * @param {Object} data - { mobile, code, password }
 * @returns {Promise} { token, refreshToken, user }
 */
export function register(data) {
  return request({ url: '/auth/register', method: 'post', data });
}

/**
 * 刷新Token：用HttpOnly Cookie中的refreshToken换取新access token
 * @returns {Promise} { token, refreshToken }
 */
export function refreshToken() {
  return request({ url: '/auth/refresh', method: 'post' });
}

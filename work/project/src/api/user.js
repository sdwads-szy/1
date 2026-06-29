import request from '@/utils/request';

// @api 用户接口 — 个人信息/收货地址CRUD

/**
 * 获取用户个人信息
 * @returns {Promise} { nickname, avatar, phone, role }
 */
export function getProfile() {
  return request({ url: '/user/profile', method: 'get' });
}

/**
 * 更新用户个人信息
 * @param {Object} data — { nickname?, avatar? }
 * @returns {Promise} { success }
 */
export function updateProfile(data) {
  return request({ url: '/user/profile', method: 'put', data });
}

/**
 * 获取收货地址列表
 * @returns {Promise} [{ id, name, phone, province, city, district, detail, isDefault }]
 */
export function getAddresses() {
  return request({ url: '/user/addresses', method: 'get' });
}

/**
 * 新增收货地址
 * @param {Object} data — { name, phone, province, city, district, detail, isDefault }
 * @returns {Promise} { id }
 */
export function createAddress(data) {
  return request({ url: '/user/addresses', method: 'post', data });
}

/**
 * 更新收货地址
 * @param {number} id — 地址ID
 * @param {Object} data — { name?, phone?, province?, city?, district?, detail?, isDefault? }
 * @returns {Promise} { success }
 */
export function updateAddress(id, data) {
  return request({ url: `/user/addresses/${id}`, method: 'put', data });
}

/**
 * 删除收货地址
 * @param {number} id — 地址ID
 * @returns {Promise} { success }
 */
export function deleteAddress(id) {
  return request({ url: `/user/addresses/${id}`, method: 'delete' });
}

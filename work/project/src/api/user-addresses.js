import request from '@/utils/request'

/**
 * 收货地址列表
 * @returns {Promise} { list: [{id, province, city, district, detail, phone, contactName, isDefault}] }
 */
export function getAddresses() {
  return request({ url: '/user/addresses', method: 'get' })
}

/**
 * 新增收货地址
 * @param {Object} data - { province, city, district, detail, phone, contactName, isDefault? }
 * @returns {Promise} { addressId }
 */
export function createAddress(data) {
  return request({ url: '/user/addresses', method: 'post', data })
}

/**
 * 修改收货地址
 * @param {number} id - 地址ID
 * @param {Object} data - 部分地址字段
 * @returns {Promise} { addressId }
 */
export function updateAddress(id, data) {
  return request({ url: `/user/addresses/${id}`, method: 'put', data })
}

/**
 * 删除收货地址
 * @param {number} id - 地址ID
 * @returns {Promise}
 */
export function deleteAddress(id) {
  return request({ url: `/user/addresses/${id}`, method: 'delete' })
}

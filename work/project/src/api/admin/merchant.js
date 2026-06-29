import request from '@/utils/request';

// @api 平台后台商家审核

/**
 * 获取商家审核列表
 * @param {Object} data - { status?, page, pageSize }
 * @returns {Promise} { list: Array, total: number }
 */
export function getMerchantList(data) {
  return request({
    url: '/admin/merchants',
    method: 'get',
    params: data
  });
}

/**
 * 获取商家详情（含资质信息）
 * @param {number|string} id - 商家ID
 * @returns {Promise} { shop: Object, qualification: Object }
 */
export function getMerchantDetail(id) {
  return request({
    url: `/admin/merchants/${id}`,
    method: 'get'
  });
}

/**
 * 审核商家资质
 * @param {number|string} id - 商家ID
 * @param {Object} data - { result: 'approved'|'rejected', note: string }
 * @returns {Promise} { success: boolean }
 */
export function reviewMerchant(id, data) {
  return request({
    url: `/admin/merchants/${id}/review`,
    method: 'put',
    data
  });
}

/**
 * 激活商家店铺
 * @param {number|string} id - 商家ID
 * @returns {Promise} { success: boolean }
 */
export function activateMerchant(id) {
  return request({
    url: `/admin/merchants/${id}/activate`,
    method: 'put'
  });
}

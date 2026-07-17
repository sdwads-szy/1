import request from '@/utils/request'

/**
 * 获取待审核商品列表
 * @param {Object} params - { page, pageSize, keyword, status, dateRange }
 * @returns {Promise} { list, total, page, pageSize, stats: { pending, todayApproved, todayRejected } }
 */
export function getReviewProducts(params) {
  return request({ url: '/admin/products', method: 'get', params })
}

/**
 * 审核商品（通过/驳回）
 * @param {number} id - 商品SPU ID
 * @param {Object} data - { action: 'approve'|'reject', reason?: string }
 * @returns {Promise} { productId, status }
 */
export function reviewProduct(id, data) {
  return request({ url: `/admin/products/${id}/review`, method: 'post', data })
}

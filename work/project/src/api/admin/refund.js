// @api 平台退款管理 API
import request from '@/utils/request'

/**
 * 获取退款列表
 * @param {Object} params - { status?, page?, pageSize?, id? }
 * @returns {Promise}
 */
export function getRefundList(params) {
  return request({ url: '/admin/refunds', method: 'get', params })
}

/**
 * 审核退款（商家端调用）
 * @param {number} id - 退款ID
 * @param {Object} data - { action: 'approved'|'rejected', note? }
 * @returns {Promise}
 */
export function approveRefund(id, data) {
  return request({ url: `/admin/refunds/${id}/approve`, method: 'put', data })
}

/**
 * 执行退款（平台管理员调用）
 * @param {number} id - 退款ID
 * @returns {Promise}
 */
export function executeRefund(id) {
  return request({ url: `/admin/refunds/${id}/execute`, method: 'post' })
}

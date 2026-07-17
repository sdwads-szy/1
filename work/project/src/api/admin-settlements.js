import request from '@/utils/request';

/**
 * 获取结算单列表（平台管理员）
 * @param {Object} params - { status?, page?, pageSize? }
 * @returns {Promise} { list, total, page, pageSize }
 */
export function getAdminSettlements(params) {
  return request({ url: '/admin/settlements', method: 'get', params });
}

/**
 * 结算打款
 * @param {number} id - 结算单ID
 * @returns {Promise} { settlementId, status }
 */
export function paySettlement(id) {
  return request({ url: `/admin/settlements/${id}/pay`, method: 'post' });
}

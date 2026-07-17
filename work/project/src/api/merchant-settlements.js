import request from '@/utils/request';

/**
 * 获取商家结算单列表
 * @param {Object} data - { page, pageSize }
 * @returns {Promise} { list: [{id, period, amount, status, paidAt}], total }
 */
export function getMerchantSettlements(data) {
  return request({ url: '/merchant/settlements', method: 'get', params: data });
}

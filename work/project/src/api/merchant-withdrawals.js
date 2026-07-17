import request from '@/utils/request';

/**
 * 提交提现申请
 * @param {Object} data - { amount, bankAccount }
 * @returns {Promise} { requestNo, status }
 */
export function submitWithdrawal(data) {
  return request({ url: '/merchant/withdrawals', method: 'post', data });
}

/**
 * 获取提现记录列表
 * @param {Object} data - { page, pageSize, status? }
 * @returns {Promise} { list: [{id, requestNo, amount, bankAccount, status, reviewReason, createdAt, paidAt}], total }
 */
export function getWithdrawals(data) {
  return request({ url: '/merchant/withdrawals', method: 'get', params: data });
}

import request from '@/utils/request';

/**
 * 获取提现申请列表（平台管理员）
 * @param {Object} params - { status?, page?, pageSize? }
 * @returns {Promise} { list, total, page, pageSize }
 */
export function getAdminWithdrawals(params) {
  return request({ url: '/admin/withdrawals', method: 'get', params });
}

/**
 * 审批提现申请（通过或驳回）
 * @param {number} id - 提现申请ID
 * @param {Object} data - { action: 'approve'|'reject', reason?: string }
 * @returns {Promise} { withdrawalId, status }
 */
export function approveWithdrawal(id, data) {
  return request({ url: `/admin/withdrawals/${id}/approve`, method: 'post', data });
}

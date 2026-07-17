import request from '@/utils/request';

/**
 * 商家售后列表：查看本店所有售后申请，按状态筛选
 * @param {Object} data - { status, page, pageSize }
 * @returns {Promise}
 */
export function getMerchantRefunds(data) {
  return request({ url: '/merchant/refunds', method: 'get', params: data });
}

/**
 * 商家审核售后申请：同意或拒绝
 * @param {Object} data - { id, action, reason }
 * @returns {Promise}
 */
export function approveRefund(data) {
  const { id, ...body } = data;
  return request({ url: `/merchant/refunds/${id}/approve`, method: 'post', data: body });
}

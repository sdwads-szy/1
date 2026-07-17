import request from '@/utils/request';

/**
 * 发起售后申请：退款或退货退款
 * @param {Object} data - { subOrderId, type, reason, amount, evidenceImages }
 * @returns {Promise}
 */
export function applyRefund(data) {
  return request({
    url: '/refunds',
    method: 'post',
    data
  });
}

/**
 * 获取售后详情：查看售后进度、协商记录
 * @param {number} id - 售后申请ID
 * @returns {Promise}
 */
export function getRefundDetail(id) {
  return request({
    url: `/refunds/${id}`,
    method: 'get'
  });
}

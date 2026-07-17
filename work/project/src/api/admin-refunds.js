import request from '@/utils/request';

/**
 * 退款仲裁工单列表
 * @param {Object} data - { status?, page?, pageSize? }
 */
export function getArbitrationList(data) {
  return request({
    url: '/admin/refunds/arbitration',
    method: 'get',
    params: data
  });
}

/**
 * 平台仲裁裁决
 * @param {Object} data - { id, ruling, reason }
 */
export function arbitrateRefund(data) {
  const { id, ...rest } = data;
  return request({
    url: `/admin/refunds/${id}/arbitrate`,
    method: 'post',
    data: rest
  });
}

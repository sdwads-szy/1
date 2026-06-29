import request from '@/utils/request';

/**
 * @api 退款模块 — 买家端退款申请/列表/详情
 */

/** 创建退款申请 */
export function createRefund(data) {
  return request({ url: '/refunds', method: 'post', data });
}

/** 获取当前用户退款列表 */
export function getRefundList(params) {
  return request({ url: '/refunds', method: 'get', params });
}

/** 获取退款详情 */
export function getRefundDetail(id) {
  return request({ url: `/refunds/${id}`, method: 'get' });
}

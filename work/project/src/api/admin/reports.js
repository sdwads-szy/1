import request from '@/utils/request';

/**
 * @api 平台后台经营报表
 * 订单漏斗、支付汇总、退款统计
 */

/**
 * 获取订单报表
 * @param {Object} params - { startDate, endDate }
 * @returns {Promise<{ totalOrders: number, totalAmount: string, byStatus: Array, byDate: Array }>}
 */
export function getOrderReports(params) {
  return request({
    url: '/admin/reports/orders',
    method: 'get',
    params
  });
}

/**
 * 获取支付报表
 * @param {Object} params - { startDate, endDate }
 * @returns {Promise<{ totalPayments: number, totalAmount: string, byChannel: Array }>}
 */
export function getPaymentReports(params) {
  return request({
    url: '/admin/reports/payments',
    method: 'get',
    params
  });
}

/**
 * 获取退款报表
 * @param {Object} params - { startDate, endDate }
 * @returns {Promise<{ totalRefunds: number, totalAmount: string, refundRate: number, byReason: Array }>}
 */
export function getRefundReports(params) {
  return request({
    url: '/admin/reports/refunds',
    method: 'get',
    params
  });
}

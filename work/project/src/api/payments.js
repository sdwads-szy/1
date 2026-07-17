import request from '@/utils/request'

/**
 * 发起支付：生成支付流水
 * @param {Object} data - { orderNo, channel }
 * @returns {Promise} { transactionNo, paymentUrl }
 */
export function initiatePayment(data) {
  return request({ url: '/payments/pay', method: 'post', data })
}

/**
 * 支付状态查询：轮询用，间隔2s，最长30s
 * @param {string} orderNo - 订单号
 * @returns {Promise} { status, orderId }
 */
export function getPaymentStatus(orderNo) {
  return request({ url: `/payments/status/${orderNo}`, method: 'get' })
}

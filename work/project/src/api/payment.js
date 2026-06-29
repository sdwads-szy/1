import request from '@/utils/request';

// @api 支付接口

/**
 * 发起支付
 * @param {number|string} id - 订单ID
 * @param {object} data - { channel: 'wxpay'|'alipay' }
 * @returns {Promise<{ payUrl: string, qrCode: string }>}
 */
export function payPayment(id, data) {
  return request({ url: `/payments/${id}/pay`, method: 'post', data });
}

/**
 * 支付网关回调（前端一般不直接调用）
 * @param {object} data - { tradeNo, orderNo, status, sign }
 * @returns {Promise<{ code: string }>}
 */
export function paymentCallback(data) {
  return request({ url: '/payments/callback', method: 'post', data });
}

/**
 * 查询支付状态
 * @param {number|string} id - 订单ID
 * @returns {Promise<{ status: string, paidAt: string }>}
 */
export function getPaymentStatus(id) {
  return request({ url: `/payments/${id}/status`, method: 'get' });
}

import request from '@/utils/request';

// @api 订单接口 — 创建/列表/详情/取消/确认收货

/**
 * 创建订单
 * @param {Object} data — { addressId, cartItemIds, couponId?, payChannel }
 * @returns {Promise} { orderId, orderNo, paymentId, payAmount }
 */
export function createOrder(data) {
  return request({ url: '/orders', method: 'post', data });
}

/**
 * 获取订单列表
 * @param {Object} params — { status?, page?, pageSize? }
 * @returns {Promise} { list, total }
 */
export function getOrderList(params) {
  return request({ url: '/orders', method: 'get', params });
}

/**
 * 获取订单详情
 * @param {number} id — 订单ID
 * @returns {Promise} { id, orderNo, status, items, address, payment, timeline }
 */
export function getOrderDetail(id) {
  return request({ url: `/orders/${id}`, method: 'get' });
}

/**
 * 取消订单
 * @param {number} id — 订单ID
 * @returns {Promise} { success }
 */
export function cancelOrder(id) {
  return request({ url: `/orders/${id}/cancel`, method: 'put' });
}

/**
 * 确认收货
 * @param {number} id — 订单ID
 * @returns {Promise} { success }
 */
export function confirmReceive(id) {
  return request({ url: `/orders/${id}/receive`, method: 'put' });
}

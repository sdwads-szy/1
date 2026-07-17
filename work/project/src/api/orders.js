import request from '@/utils/request'

/**
 * 创建订单：从购物车勾选项生成订单
 * @param {Object} data - { addressId, cartItemIds }
 * @returns {Promise} { orderId, orderNo, totalAmount, status }
 */
export function createOrder(data) {
  return request({ url: '/orders', method: 'post', data })
}

/**
 * 我的订单列表：按状态筛选，支持分页
 * @param {Object} params - { status?, page?, pageSize? }
 * @returns {Promise} { list, total, page, pageSize }
 */
export function getOrders(params) {
  return request({ url: '/orders', method: 'get', params })
}

/**
 * 订单详情：含物流进度、订单明细
 * @param {number} id - 订单ID
 * @returns {Promise} { order, subOrders, shipments, address }
 */
export function getOrderDetail(id) {
  return request({ url: `/orders/${id}`, method: 'get' })
}

/**
 * 确认收货：将订单状态变为已完成
 * @param {number} id - 订单ID
 * @returns {Promise} { orderId, status }
 */
export function confirmReceive(id) {
  return request({ url: `/orders/${id}/confirm`, method: 'put' })
}

import request from '@/utils/request';

// @api 平台后台订单管理 — basePath: /admin/orders
const BASE = '/admin/orders';

/**
 * 获取订单列表（多条件筛选）
 * @param {Object} params — { orderNo?, status?, shopId?, startDate?, endDate?, page, pageSize }
 * @returns {Promise<{list: Array, total: number}>}
 */
export function getOrderList(params) {
  return request({ url: BASE, method: 'get', params });
}

/**
 * 获取订单详情（含 items / payment / refund / timeline）
 * @param {number} id
 * @returns {Promise<{order: Object, items: Array, payment: Object, refund: Object|null, timeline: Array}>}
 */
export function getOrderDetail(id) {
  return request({ url: `${BASE}/${id}`, method: 'get' });
}

/**
 * 发货（商家权限）
 * @param {number} id
 * @param {Object} data
 * @returns {Promise<{success: boolean}>}
 */
export function shipOrder(id, data) {
  return request({ url: `${BASE}/${id}/ship`, method: 'put', data });
}

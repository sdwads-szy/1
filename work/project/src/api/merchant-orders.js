import request from '@/utils/request';

/**
 * 商家订单列表：查看本店所有订单，按状态筛选，支持分页
 * @param {Object} data - { status, page, pageSize }
 * @returns {Promise} { list, total, page, pageSize }
 */
export function getMerchantOrders(data) {
  return request({
    url: '/merchant/orders',
    method: 'get',
    params: data
  });
}

/**
 * 商家发货：录入物流单号和承运商
 * @param {Object} data - { id, trackingNo, carrierCode }
 * @returns {Promise} { shipmentId, status }
 */
export function shipOrder(data) {
  return request({
    url: `/merchant/orders/${data.id}/ship`,
    method: 'post',
    data
  });
}

import request from '@/utils/request';

/**
 * @api 平台全局订单查询
 * @description 查看所有订单，支持订单号/状态/店铺ID多条件筛选 + 分页
 */
export function getAdminOrders(data) {
  return request({
    url: '/admin/orders',
    method: 'get',
    params: data
  });
}

import request from '@/utils/request';

/**
 * 获取商家经营数据看板
 * 返回今日GMV、今日订单数、近7天趋势数据
 * @returns {Promise<{todayGmv: string, todayOrders: number, trend: Array}>}
 */
export function getMerchantDashboard() {
  return request({
    url: '/merchant/dashboard',
    method: 'get'
  });
}

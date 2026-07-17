import request from '@/utils/request';

/**
 * 获取平台数据看板核心指标
 * @returns {Promise} { todayGmv, todayOrders, todayPaidOrders, refundRate, trend[] }
 */
export function getAdminDashboard() {
  return request({
    url: '/admin/dashboard',
    method: 'get'
  });
}

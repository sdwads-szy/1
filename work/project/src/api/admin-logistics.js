import request from '@/utils/request';

/**
 * @api 物流监控 - 平台管理员物流商接口状态与异常监控
 */

/**
 * 获取物流监控数据：异常物流单数、查询超时次数、最近异常记录
 * @param {Object} data - 请求参数（当前无参数）
 * @returns {Promise} { abnormalShipments, timeoutQueries, recentErrors }
 */
export function getLogisticsMonitor(data) {
  return request({
    url: '/admin/logistics/monitor',
    method: 'get',
    params: data
  });
}

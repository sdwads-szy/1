const adminLogisticsService = require('../services/adminLogisticsService');
const response = require('../utils/response');

/**
 * GET /api/admin/logistics
 * 物流概览：返回 KPI 概览数据
 */
const getLogisticsOverview = async (req, res) => {
  try {
    const data = await adminLogisticsService.getOverview();
    response.success(res, data, '获取物流概览成功');
  } catch (error) {
    if (error.message === 'FORBIDDEN' || error.status === 403) {
      response.error(res, '无权限访问', 403);
    } else {
      response.error(res, '获取物流概览失败');
    }
  }
};

/**
 * GET /api/admin/logistics/monitor
 * 物流监控：返回异常物流单数、查询超时次数、最近异常记录
 */
const getMonitor = async (req, res) => {
  try {
    const data = await adminLogisticsService.getMonitor();
    response.success(res, data, '获取物流监控数据成功');
  } catch (error) {
    if (error.message === 'FORBIDDEN' || error.status === 403) {
      response.error(res, '无权限访问', 403);
    } else {
      response.error(res, '获取物流监控数据失败');
    }
  }
};

module.exports = { getMonitor, getLogisticsOverview };

const adminDashboardService = require('../services/adminDashboardService');
const response = require('../utils/response');

/**
 * GET /api/admin/dashboard
 * 平台数据看板：今日GMV/订单量/退款率 + 近7天趋势
 */
 async function getAdminDashboard(req, res) {
  try {
     // 平台看板核心字段: stat_date, gmv, order_count, paid_order_count, refund_rate, commission
    const data = await adminDashboardService.getAdminDashboard();
    response.success(res, data, '获取看板数据成功');
  } catch (err) {
    const errorMap = { FORBIDDEN: 403 };
    const status = errorMap[err.message] || 500;
    response.error(res, err.message || '获取看板数据失败', status);
  }
}

 module.exports = { getAdminDashboard };

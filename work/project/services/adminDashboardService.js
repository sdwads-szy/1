const db = require('../config/db');

/**
 * 平台数据看板核心逻辑
 * - 今日实时指标：GMV / 订单数 / 支付订单数 / 退款率
 * - 近7天趋势数据
 * @returns {{ todayGmv: string, todayOrders: number, todayPaidOrders: number, refundRate: string, trend: array }}
 */
async function getAdminDashboard() {
  // Step 1: 今日实时指标 — 使用 idx_stat_date 索引
  const todayRows = await db.query(
    'SELECT stat_date, gmv, order_count, paid_order_count, refund_rate, commission FROM platform_daily_stats WHERE stat_date = CURDATE()'
  );

  const trendRows = await db.query(
    'SELECT stat_date, gmv, order_count, paid_order_count, refund_rate, commission FROM platform_daily_stats WHERE stat_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 6 DAY) AND CURDATE() ORDER BY stat_date DESC'
  );

  // 今日数据可能尚未生成 → 安全默认值
  const today = todayRows.length > 0 ? todayRows[0] : {
    gmv: '0.00',
    order_count: 0,
    paid_order_count: 0,
    refund_rate: '0.0000'
  };

  // 趋势数据转换为 camelCase 响应格式
  const trend = trendRows.map(row => ({
    statDate: row.stat_date,
    gmv: row.gmv,
    orderCount: row.order_count,
    paidOrderCount: row.paid_order_count,
    refundRate: row.refund_rate
  }));

  return {
    todayGmv: today.gmv,
    todayOrders: today.order_count,
    todayPaidOrders: today.paid_order_count,
    refundRate: today.refund_rate,
    trend
  };
}

module.exports = { getAdminDashboard };

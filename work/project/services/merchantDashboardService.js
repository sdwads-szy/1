const db = require('../config/db');

/**
 * 商家经营数据看板
 * @param {number} merchantId - 商家ID
 * @returns {{ todayGmv: string, todayOrders: number, trend: Array<{statDate: string, gmv: string, orderCount: number}> }}
 */
async function getMerchantDashboard(merchantId) {
  // Step 1: 今日实时指标 — 使用 idx_merchant_date 索引
  const todayRows = await db.query(
    'SELECT gmv, order_count FROM merchant_daily_stats WHERE merchant_id = ? AND stat_date = CURDATE()',
    [merchantId]
  );

  const todayGmv = todayRows.length > 0 ? todayRows[0].gmv : '0.00';
  const todayOrders = todayRows.length > 0 ? todayRows[0].order_count : 0;

  // Step 2: 近7天趋势 — 使用 idx_merchant_date 索引
  const trendRows = await db.query(
    'SELECT stat_date, gmv, order_count FROM merchant_daily_stats WHERE merchant_id = ? AND stat_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND CURDATE() ORDER BY stat_date DESC',
    [merchantId]
  );

  const trend = trendRows.map(row => ({
    statDate: row.stat_date,
    gmv: row.gmv,
    orderCount: row.order_count
  }));

  return { todayGmv, todayOrders, trend };
}

module.exports = { getMerchantDashboard };

const response = require('../utils/response');
const db = require('../config/db');
const { getMerchantDashboard } = require('../services/merchantDashboardService');

/**
 * GET /api/merchant/dashboard
 * 商家经营数据看板：实时指标 + 近7天趋势
 */
async function getDashboard(req, res) {
  try {
    const userId = req.userId;

    // 通过 userId 查找对应的 merchant_id
    const merchants = await db.query('SELECT id FROM merchants WHERE user_id = ?', [userId]);
    if (!merchants.length) {
      return response.fail(res, '店铺不存在', 404);
    }
    const merchantId = merchants[0].id;

    const data = await getMerchantDashboard(merchantId);
    response.success(res, data, '获取经营数据成功');
  } catch (e) {
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    response.error(res, '获取经营数据失败');
  }
}

module.exports = { getDashboard };

const response = require('../utils/response');
const adminOrderService = require('../services/adminOrderService');

const VALID_STATUSES = ['pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunding', 'refunded'];

/**
 * GET /api/admin/orders
 * 平台全局订单查询：查看所有订单，支持多条件筛选
 * @param {Object} req.query - { orderNo?, status?, shopId?, page?, pageSize? }
 * @returns {Object} { list, total, page, pageSize }
 */
async function getAdminOrders(req, res) {
  try {
    const { orderNo, status, shopId, page, pageSize } = req.query;

    // 校验 status 枚举值
    if (status && !VALID_STATUSES.includes(status)) {
      return response.fail(res, '无效的订单状态', 400);
    }

    const result = await adminOrderService.getAdminOrders({
      orderNo: orderNo || undefined,
      status: status || undefined,
      shopId: shopId ? parseInt(shopId, 10) : undefined,
      page: page ? Math.max(1, parseInt(page, 10)) : 1,
      pageSize: pageSize ? Math.min(50, Math.max(1, parseInt(pageSize, 10))) : 20
    });

    response.success(res, result);
  } catch (e) {
    response.fail(res, e.message || '查询订单失败', 500);
  }
}

module.exports = { getAdminOrders };

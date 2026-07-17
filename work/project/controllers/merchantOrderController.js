const response = require('../utils/response');
const merchantOrderService = require('../services/merchantOrderService');

/**
 * GET /api/merchant/orders
 * 商家查询自己店铺的订单列表
 */
async function getOrderList(req, res) {
  try {
    const page = Math.max(parseInt(req.query.page) || 1, 1);
    const pageSize = Math.min(Math.max(parseInt(req.query.pageSize) || 20, 1), 100);
    const status = req.query.status || null;

    const result = await merchantOrderService.getOrderList(req.userId, { page, pageSize, status });
    response.success(res, result, '查询成功');
  } catch (err) {
    const errorMap = {
      'NOT_MERCHANT': [403, '无权操作'],
      'NO_SHOP': [404, '店铺不存在'],
    };
    const [code, msg] = errorMap[err.message] || [500, '服务器内部错误'];
    response.fail(res, msg, code);
  }
}

/**
 * POST /api/merchant/orders/:id/ship
 * 商家对已付款子订单进行发货
 */
async function shipOrder(req, res) {
  try {
    const subOrderId = parseInt(req.params.id);
    if (!subOrderId || subOrderId < 1) {
      return response.fail(res, '订单ID无效', 400);
    }

    const { trackingNo, carrierCode } = req.body;
    if (!trackingNo || !carrierCode) {
      return response.fail(res, '物流单号和快递公司代码不能为空', 400);
    }
    if (typeof trackingNo !== 'string' || trackingNo.length > 64) {
      return response.fail(res, '物流单号格式无效', 400);
    }
    if (typeof carrierCode !== 'string' || carrierCode.length > 32) {
      return response.fail(res, '快递公司代码格式无效', 400);
    }

    const shipment = await merchantOrderService.shipOrder(req.userId, subOrderId, trackingNo.trim(), carrierCode.trim());
    response.success(res, shipment, '发货成功');
  } catch (err) {
    const errorMap = {
      'NOT_MERCHANT': [403, '无权操作'],
      'NO_SHOP': [404, '店铺不存在'],
      'SUB_ORDER_NOT_FOUND': [404, '子订单不存在'],
      'NOT_BELONG_TO_SHOP': [403, '无权操作此订单'],
      'ORDER_STATUS': [422, '当前订单状态不可发货'],
      'SHIPMENT_EXISTS': [409, '该订单已发货，不能重复发货'],
      'CONCURRENCY_CONFLICT': [409, '订单状态已变更，请刷新重试'],
    };
    const [code, msg] = errorMap[err.message] || [500, '服务器内部错误'];
    response.fail(res, msg, code);
  }
}

module.exports = { getOrderList, shipOrder };

const orderService = require('../services/orderService');
const response = require('../utils/response');

/**
 * POST /api/orders — 创建订单（下单结算）
 * 场景树 S5: 下单结算
 */
async function createOrder(req, res) {
  try {
    const userId = req.userId;
    const { addressId, cartItemIds, paymentMethod, remark } = req.body;

    const result = await orderService.createOrder(userId, addressId, cartItemIds, paymentMethod, remark);

    return response.success(res, result, '下单成功');
  } catch (e) {
    const errorMapping = {
      'MISSING_ADDRESS':        { status: 400, message: '请选择收货地址' },
      'EMPTY_CART':     { status: 400, message: '请选择商品' },
      'INVALID_PAYMENT_METHOD': { status: 400, message: '不支持的支付方式' },
      'INVALID_ADDRESS':        { status: 400, message: '收货地址无效' },
      'CART_ITEMS_NOT_FOUND':   { status: 400, message: '购物车商品不存在或已失效，请刷新后重试' },
      'SHOP_FROZEN':            { status: 422, message: `店铺「${e.shopName || '未知'}」已暂停营业，请移除该店铺商品后重试` },
      'STOCK_INSUFFICIENT':     { status: 422, message: e.availableStock !== undefined ? `「${e.skuName || '商品'}」库存不足，仅剩 ${e.availableStock} 件` : '库存不足，请重新选择' },
      'SKU_NOT_FOUND':          { status: 500, message: '系统错误，请稍后重试' },
    };

    const mapped = errorMapping[e.message];
    if (mapped) {
      return response.fail(res, mapped.message, mapped.status);
    }

    return response.error(res, '下单失败，请稍后重试');
  }
}

/**
 * GET /api/orders — 获取用户订单列表
 * 支持 ?status=xxx &page=1&pageSize=20
 */
 async function listOrders(req, res) {
  try {
    const userId = req.userId;
    const { status, page, pageSize } = req.query;

    const result = await orderService.getOrders(userId, {
      status: status || undefined,
      page: parseInt(page) || 1,
      pageSize: Math.min(parseInt(pageSize) || 20, 100)
    });

    return response.success(res, result);
  } catch (e) {
    return response.error(res, '获取订单列表失败');
  }
}

/**
 * GET /api/orders/:id — 获取订单详情
 */
async function getOrderDetail(req, res) {
  try {
    const userId = req.userId;
    const orderId = parseInt(req.params.id);

    if (!orderId || orderId < 1) {
      return response.fail(res, '订单ID无效', 400);
    }

    const result = await orderService.getOrderDetail(userId, orderId);

    return response.success(res, result);
  } catch (e) {
    const errorMapping = {
      'ORDER_NOT_FOUND': { status: 404, message: '订单不存在' },
      'ORDER_NOT_BELONG': { status: 403, message: '无权查看此订单' },
    };

    const mapped = errorMapping[e.message];
    if (mapped) {
      return response.fail(res, mapped.message, mapped.status);
    }

    return response.error(res, '获取订单详情失败');
  }
}

/**
 * POST /api/orders/:id/confirm — 确认收货
 * 场景树 S9: 确认收货
 */
async function confirmReceive(req, res) {
  try {
    const userId = req.userId;
    const orderId = parseInt(req.params.id);

    if (!orderId || orderId < 1) {
      return response.fail(res, '订单ID无效', 400);
    }

    const result = await orderService.confirmReceive(userId, orderId);

    return response.success(res, result, '确认收货成功');
  } catch (e) {
    const errorMapping = {
      'ORDER_NOT_FOUND': { status: 404, message: '订单不存在' },
      'ORDER_NOT_BELONG': { status: 403, message: '无权操作此订单' },
      'INVALID_STATUS': { status: 422, message: '当前订单状态不可确认收货，请刷新后重试' },
    };

    const mapped = errorMapping[e.message];
    if (mapped) {
      return response.fail(res, mapped.message, mapped.status);
    }

    return response.error(res, '确认收货失败，请稍后重试');
  }
}

module.exports = {
  createOrder,
   listOrders,
  getOrderDetail,
  confirmReceive
};

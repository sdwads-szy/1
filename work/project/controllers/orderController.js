const orderService = require('../services/orderService');
const response = require('../utils/response');

const orderController = {
  /**
   * POST /api/orders — 创建订单
   */
  async createOrder(req, res) {
    try {
      const { addressId, cartItemIds, couponId, payChannel } = req.body;
      const result = await orderService.createOrder(req.userId, {
        addressId,
        cartItemIds,
        couponId,
        payChannel
      });
      response.success(res, result, '下单成功');
    } catch (e) {
      const errorMap = {
        'CART_EMPTY': { status: 400, message: '购物车为空' },
        'ADDRESS_REQUIRED': { status: 400, message: '请选择收货地址' },
        'INVALID_PAY_CHANNEL': { status: 400, message: '无效的支付渠道' },
        'INSUFFICIENT_STOCK': { status: 422, message: '库存不足' },
        'COUPON_INVALID': { status: 422, message: '优惠券不可用' },
        'PRODUCT_UNAVAILABLE': { status: 422, message: '商品已下架' }
      };
      const mapped = errorMap[e.message];
      if (mapped) {
        response.fail(res, mapped.message, mapped.status);
      } else {
        response.error(res, e.message || '下单失败');
      }
    }
  },

  /**
   * GET /api/orders — 用户订单列表
   */
  async getOrderList(req, res) {
    try {
      const { status, page, pageSize } = req.query;
      const result = await orderService.getOrderList(req.userId, { status, page, pageSize });
      response.success(res, result);
    } catch (e) {
      response.error(res, e.message || '获取订单列表失败');
    }
  },

  /**
   * GET /api/orders/:id — 用户订单详情
   */
  async getOrderDetail(req, res) {
    try {
      const result = await orderService.getOrderDetail(parseInt(req.params.id), req.userId);
      response.success(res, result);
    } catch (e) {
      if (e.message === 'NOT_FOUND') {
        response.fail(res, '订单不存在', 404);
      } else {
        response.error(res, e.message || '获取订单详情失败');
      }
    }
  },

  /**
   * PUT /api/orders/:id/cancel — 取消订单
   */
  async cancelOrder(req, res) {
    try {
      const result = await orderService.cancelOrder(parseInt(req.params.id), req.userId);
      response.success(res, result, '订单已取消');
    } catch (e) {
      const errorMap = {
        'NOT_FOUND': { status: 404, message: '订单不存在' },
        'ORDER_CANNOT_CANCEL': { status: 422, message: '当前订单状态不可取消' }
      };
      const mapped = errorMap[e.message];
      if (mapped) {
        response.fail(res, mapped.message, mapped.status);
      } else {
        response.error(res, e.message || '取消订单失败');
      }
    }
  },

  /**
   * PUT /api/orders/:id/receive — 确认收货
   */
  async confirmReceipt(req, res) {
    try {
      const result = await orderService.confirmReceipt(parseInt(req.params.id), req.userId);
      response.success(res, result, '确认收货成功');
    } catch (e) {
      const errorMap = {
        'NOT_FOUND': { status: 404, message: '订单不存在' },
        'ORDER_NOT_SHIPPED': { status: 422, message: '订单未发货，无法确认收货' }
      };
      const mapped = errorMap[e.message];
      if (mapped) {
        response.fail(res, mapped.message, mapped.status);
      } else {
        response.error(res, e.message || '确认收货失败');
      }
    }
  },

  // ===================== 管理端 =====================

  /**
   * GET /api/admin/orders — 管理端订单列表
   */
  async adminGetOrderList(req, res) {
    try {
      const { orderNo, status, shopId, startDate, endDate, page, pageSize } = req.query;
      const result = await orderService.adminGetOrderList({
        orderNo, status, shopId, startDate, endDate, page, pageSize
      });
      response.success(res, result);
    } catch (e) {
      response.error(res, e.message || '获取订单列表失败');
    }
  },

  /**
   * GET /api/admin/orders/:id — 管理端订单详情
   */
  async adminGetOrderDetail(req, res) {
    try {
      const result = await orderService.adminGetOrderDetail(parseInt(req.params.id));
      response.success(res, result);
    } catch (e) {
      if (e.message === 'NOT_FOUND') {
        response.fail(res, '订单不存在', 404);
      } else {
        response.error(res, e.message || '获取订单详情失败');
      }
    }
  },

  /**
   * PUT /api/admin/orders/:id/ship — 商家发货
   */
  async shipOrder(req, res) {
    try {
      const result = await orderService.shipOrder(parseInt(req.params.id), req.userId);
      response.success(res, result, '发货成功');
    } catch (e) {
      const errorMap = {
        'NOT_FOUND': { status: 404, message: '订单不存在' },
        'NOT_MERCHANT': { status: 403, message: '非商家用户，无法操作' },
        'NOT_ORDER_OWNER': { status: 403, message: '无权操作此订单' },
        'ORDER_NOT_PAID': { status: 422, message: '订单未支付，无法发货' }
      };
      const mapped = errorMap[e.message];
      if (mapped) {
        response.fail(res, mapped.message, mapped.status);
      } else {
        response.error(res, e.message || '发货失败');
      }
    }
  }
};

module.exports = orderController;

const response = require('../utils/response');
const orderQueryService = require('../services/orderQueryService');

/**
 * GET /api/orders
 * 我的订单列表：支持状态筛选和分页
 */
async function getOrders(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const pageNum = Math.max(1, parseInt(page) || 1);
    const size = Math.min(50, Math.max(1, parseInt(pageSize) || 20));

    // 校验 status 枚举值
    const validStatuses = ['pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunding', 'refunded'];
    if (status && !validStatuses.includes(status)) {
      return response.fail(res, '无效的订单状态', 400);
    }

    const result = await orderQueryService.getOrdersByUser(req.userId, {
      status: status || null,
      page: pageNum,
      pageSize: size,
    });

    // 为每个订单填充子订单和明细
    const list = [];
    for (const order of result.list) {
      const subOrders = await orderQueryService.getSubOrdersByOrder(order.id);
      const enrichedSubOrders = [];
      for (const sub of subOrders) {
        const items = await orderQueryService.getOrderItems(sub.id);
        enrichedSubOrders.push({
          id: sub.id,
          subOrderNo: sub.sub_order_no,
          shopId: sub.shop_id,
          shopName: sub.shop_name || null,
          amount: sub.amount,
          status: sub.status,
          createdAt: sub.created_at,
          items: items.map(item => ({
            skuId: item.sku_id,
            quantity: item.quantity,
            price: item.price,
            snapshot: item.snapshot,
          })),
        });
      }
      list.push({
        id: order.id,
        orderNo: order.order_no,
        totalAmount: order.total_amount,
        status: order.status,
        paidAt: order.paid_at,
        createdAt: order.created_at,
        subOrders: enrichedSubOrders,
      });
    }

    response.success(res, {
      list,
      total: result.total,
      page: result.page,
      pageSize: result.pageSize,
    });
  } catch (e) {
    response.error(res, e.message);
  }
}

/**
 * GET /api/orders/:id
 * 订单详情：含子订单、订单明细、物流信息
 */
async function getOrderDetail(req, res) {
  try {
    const id = parseInt(req.params.id);
    if (!id || id < 1) {
      return response.fail(res, '参数错误', 400);
    }

    const order = await orderQueryService.getOrderById(id);

    // 数据所有权校验
    if (order.user_id !== req.userId) {
      return response.fail(res, '无权查看此订单', 403);
    }

    // 查询子订单
    const subOrders = await orderQueryService.getSubOrdersByOrder(id);
    const enrichedSubOrders = [];
    for (const sub of subOrders) {
      const items = await orderQueryService.getOrderItems(sub.id);
      enrichedSubOrders.push({
        id: sub.id,
        subOrderNo: sub.sub_order_no,
        shopId: sub.shop_id,
        shopName: sub.shop_name || null,
        amount: sub.amount,
        status: sub.status,
        createdAt: sub.created_at,
        items: items.map(item => ({
          skuId: item.sku_id,
          quantity: item.quantity,
          price: item.price,
          snapshot: item.snapshot,
        })),
      });
    }

    // shipments 和 address 由对应模块补充，当前返回空
    response.success(res, {
      order: {
        id: order.id,
        orderNo: order.order_no,
        totalAmount: order.total_amount,
        status: order.status,
        paidAt: order.paid_at,
        createdAt: order.created_at,
      },
      subOrders: enrichedSubOrders,
      shipments: [],
      address: null,
    });
  } catch (e) {
    if (e.message === 'ORDER_NOT_FOUND') {
      return response.fail(res, '订单不存在', 404);
    }
    response.error(res, e.message);
  }
}

/**
 * POST /api/orders/:id/confirm
 * 确认收货：将订单和子订单状态从 shipped 变更为 completed
 */
async function confirmReceive(req, res) {
  try {
    const id = parseInt(req.params.id);
    if (!id || id < 1) {
      return response.fail(res, '参数错误', 400);
    }

    const result = await orderQueryService.confirmReceive(id, req.userId);
    response.success(res, result);
  } catch (e) {
    if (e.message === 'ORDER_NOT_FOUND') {
      return response.fail(res, '订单不存在', 404);
    }
    if (e.message === 'NOT_OWN_ORDER') {
      return response.fail(res, '无权操作此订单', 403);
    }
    if (e.message === 'ORDER_STATUS_INVALID') {
      return response.fail(res, '订单状态已变更，请刷新', 409);
    }
    response.error(res, e.message);
  }
}

module.exports = { getOrders, getOrderDetail, confirmReceive };

const refundService = require('../services/refundService');
const response = require('../utils/response');

/**
 * 买家申请退款
 * POST /api/refunds
 */
async function applyRefund(req, res) {
  try {
    const { orderId, reason, amount, evidenceImages } = req.body;
    const userId = req.userId;

    if (!orderId || !reason || !amount) {
      return response.fail(res, '缺少必要参数（orderId, reason, amount）', 400);
    }

    const numAmount = parseFloat(amount);
    if (!Number.isFinite(numAmount) || numAmount <= 0) {
      return response.fail(res, '退款金额必须为正数', 400);
    }

    const result = await refundService.applyRefund(userId, orderId, reason, amount, evidenceImages);
    response.success(res, result, '退款申请已提交');
  } catch (e) {
    const errorMap = {
      'ORDER_NOT_REFUNDABLE': [422, '当前订单状态不可退款'],
      'REFUND_DUPLICATE': [409, '已存在进行中的退款申请'],
      'AMOUNT_EXCEED': [422, '退款金额不可超过原支付金额'],
      'ORDER_NOT_FOUND': [404, '订单不存在']
    };
    const [code, message] = errorMap[e.message] || [500, '服务器内部错误'];
    response.fail(res, message, code);
  }
}

/**
 * 买家查看自己的退款列表
 * GET /api/refunds
 */
async function getUserRefunds(req, res) {
  try {
    const userId = req.userId;
    const refunds = await refundService.getUserRefunds(userId);
    response.success(res, { list: refunds, total: refunds.length });
  } catch (e) {
    response.fail(res, '获取退款列表失败', 500);
  }
}

/**
 * 买家查看退款详情
 * GET /api/refunds/:id
 */
async function getRefundDetail(req, res) {
  try {
    const refundId = parseInt(req.params.id) || 0;
    const refund = await refundService.getRefundById(refundId);

    if (refund.userId !== req.userId) {
      return response.fail(res, '无权查看该退款单', 403);
    }

    response.success(res, refund);
  } catch (e) {
    const errorMap = {
      'REFUND_NOT_FOUND': [404, '退款单不存在']
    };
    const [code, message] = errorMap[e.message] || [500, '服务器内部错误'];
    response.fail(res, message, code);
  }
}

/**
 * 管理员查看退款列表
 * GET /api/admin/refunds
 */
async function listRefunds(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const result = await refundService.listRefunds({ status, page, pageSize });
    response.success(res, result);
  } catch (e) {
    response.fail(res, '获取退款列表失败', 500);
  }
}

/**
 * 商家审批退款
 * PUT /api/admin/refunds/:id/approve
 */
async function approveRefund(req, res) {
  try {
    const refundId = parseInt(req.params.id) || 0;
    const merchantId = req.userId;
    const { action, note } = req.body;

    if (!action || !['approved', 'rejected'].includes(action)) {
      return response.fail(res, 'action 必须为 approved 或 rejected', 400);
    }

    const result = await refundService.approveRefund(refundId, merchantId, action, note);
    response.success(res, result, action === 'approved' ? '已同意退款' : '已拒绝退款');
  } catch (e) {
    const errorMap = {
      'REFUND_NOT_FOUND': [404, '退款单不存在'],
      'NOT_MERCHANT_OWNER': [403, '无权操作此退款单'],
      'ALREADY_PROCESSED': [409, '退款单已处理']
    };
    const [code, message] = errorMap[e.message] || [500, '服务器内部错误'];
    response.fail(res, message, code);
  }
}

/**
 * 平台管理员执行退款
 * POST /api/admin/refunds/:id/execute
 */
async function executeRefund(req, res) {
  try {
    const refundId = parseInt(req.params.id) || 0;
    const result = await refundService.executeRefund(refundId);
    response.success(res, result, '退款执行成功');
  } catch (e) {
    const errorMap = {
      'REFUND_NOT_FOUND': [404, '退款单不存在'],
      'REFUND_NOT_APPROVED': [422, '退款未审批，无法执行'],
      'GATEWAY_REFUND_FAIL': [502, '退款网关异常，将自动重试']
    };
    const [code, message] = errorMap[e.message] || [500, '服务器内部错误'];
    response.fail(res, message, code);
  }
}

module.exports = {
  applyRefund,
  getUserRefunds,
  getRefundDetail,
  listRefunds,
  approveRefund,
  executeRefund
};

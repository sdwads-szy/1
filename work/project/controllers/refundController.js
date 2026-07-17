const refundService = require('../services/refundService');
const response = require('../utils/response');

/**
 * 消费者 — 申请售后
 * POST /api/refunds
 */
async function applyRefund(req, res) {
  try {
    const { subOrderId, type, reason, amount, evidenceImages } = req.body;

    if (!subOrderId) return response.fail(res, '请提供子订单ID', 400);
    if (!type || !['only_refund', 'return_refund'].includes(type)) {
      return response.fail(res, '售后类型无效', 400);
    }
    if (!reason || !reason.trim()) return response.fail(res, '请填写售后原因', 400);
    if (!amount || isNaN(amount) || Number(amount) <= 0) {
      return response.fail(res, '退款金额无效', 400);
    }

    const result = await refundService.createRefundRequest(req.userId, {
      subOrderId: Number(subOrderId),
      type,
      reason: reason.trim(),
      amount: Number(amount),
      evidenceImages: evidenceImages || [],
    });

    return response.success(res, result, '售后申请已提交');
  } catch (e) {
    const errorMap = {
      SUB_ORDER_NOT_FOUND: [404, '子订单不存在'],
      FORBIDDEN: [403, '无权操作此订单'],
      ORDER_STATUS_NOT_ALLOWED: [422, '当前订单状态不可申请售后'],
      DUPLICATE_REFUND: [422, '已有进行中的售后单'],
      AMOUNT_EXCEEDS_PAID: [422, '退款金额不能超过实付金额'],
    };
    const [code, msg] = errorMap[e.message] || [500, '系统错误'];
    return response.fail(res, msg, code);
  }
}

/**
 * 消费者/商家/管理员 — 查看售后详情
 * GET /api/refunds/:id
 */
async function getRefundDetail(req, res) {
  try {
    const refundId = parseInt(req.params.id, 10);
    if (!refundId) return response.fail(res, '售后单ID无效', 400);

    const result = await refundService.getRefundRequest(refundId, req.userId, req.user.role);
    return response.success(res, result);
  } catch (e) {
    const errorMap = {
      REFUND_NOT_FOUND: [404, '售后单不存在'],
      FORBIDDEN: [403, '无权查看此售后单'],
    };
    const [code, msg] = errorMap[e.message] || [500, '系统错误'];
    return response.fail(res, msg, code);
  }
}

/**
 * 商家 — 审批售后（同意/拒绝）
 * POST /api/merchant/refunds/:id/approve
 */
async function approveRefund(req, res) {
  try {
    const refundId = parseInt(req.params.id, 10);
    const { action, reason } = req.body;

    if (!refundId) return response.fail(res, '售后单ID无效', 400);
    if (!action || !['approve', 'reject'].includes(action)) {
      return response.fail(res, '操作无效，可选 approve 或 reject', 400);
    }

    const result = await refundService.approveRefundRequest(
      refundId, req.userId, action, (reason || '').trim() || null
    );

    const msg = action === 'approve' ? '已同意售后申请' : '已拒绝售后申请';
    return response.success(res, result, msg);
  } catch (e) {
    const errorMap = {
      REFUND_NOT_FOUND: [404, '售后单不存在'],
      FORBIDDEN: [403, '无权操作此售后单'],
      STATUS_CONFLICT: [409, '售后单状态已变更，请刷新'],
      INVALID_ACTION: [400, '无效操作'],
    };
    const [code, msg] = errorMap[e.message] || [500, '系统错误'];
    return response.fail(res, msg, code);
  }
}

/**
 * 商家 — 售后列表
 * GET /api/merchant/refunds
 */
async function listMerchantRefunds(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const result = await refundService.listMerchantRefunds(req.userId, {
      status: status || null,
      page: Math.max(1, parseInt(page, 10) || 1),
      pageSize: Math.min(100, Math.max(1, parseInt(pageSize, 10) || 20)),
    });
    return response.success(res, result);
  } catch (e) {
    const errorMap = {
      FORBIDDEN: [403, '无权操作'],
    };
    const [code, msg] = errorMap[e.message] || [500, '系统错误'];
    return response.fail(res, msg, code);
  }
}

/**
 * 平台管理员 — 仲裁工单列表
 * GET /api/admin/refunds/arbitration
 */
async function listArbitrationRefunds(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const result = await refundService.listArbitrationRefunds({
      status: status || null,
      page: Math.max(1, parseInt(page, 10) || 1),
      pageSize: Math.min(100, Math.max(1, parseInt(pageSize, 10) || 20)),
    });
    return response.success(res, result);
  } catch (e) {
    return response.fail(res, '系统错误', 500);
  }
}

/**
 * 平台管理员 — 仲裁裁决
 * POST /api/admin/refunds/:id/arbitrate
 */
async function arbitrateRefund(req, res) {
  try {
    const refundId = parseInt(req.params.id, 10);
    const { ruling, reason } = req.body;

    if (!refundId) return response.fail(res, '售后单ID无效', 400);
    if (!ruling || !['force_refund', 'dismiss'].includes(ruling)) {
      return response.fail(res, '裁决类型无效，可选 force_refund 或 dismiss', 400);
    }

    const result = await refundService.arbitrateRefund(
      refundId, req.userId, ruling, (reason || '').trim() || null
    );

    const msg = ruling === 'force_refund' ? '已强制退款' : '已驳回仲裁';
    return response.success(res, result, msg);
  } catch (e) {
    const errorMap = {
      REFUND_NOT_FOUND: [404, '售后单不存在'],
      STATUS_CONFLICT: [409, '售后单状态已变更，请刷新'],
      INVALID_RULING: [400, '无效裁决'],
    };
    const [code, msg] = errorMap[e.message] || [500, '系统错误'];
    return response.fail(res, msg, code);
  }
}

module.exports = {
  applyRefund,
  getRefundDetail,
  approveRefund,
  listMerchantRefunds,
  listArbitrationRefunds,
  arbitrateRefund,
};

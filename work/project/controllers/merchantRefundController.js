const refundService = require('../services/merchantRefundService');
const response = require('../utils/response');

/**
 * GET /api/merchant/refunds
 * 获取本店铺的售后申请列表
 */
async function listShopRefunds(req, res) {
  try {
    const { page, pageSize, status, type, requestNo } = req.query;
    const filters = {};
    if (status) filters.status = status;
    if (type) filters.type = type;
    if (requestNo) filters.requestNo = requestNo;

    const result = await refundService.getMerchantRefundList(
      req.userId,
      Number(page) || 1,
      Number(pageSize) || 20,
      filters
    );
    response.success(res, result);
  } catch (e) {
    if (e.message === 'NOT_MERCHANT') {
      return response.forbidden(res, '无权操作，非商家身份');
    }
    response.error(res, e.message || '获取售后列表失败');
  }
}

/**
 * POST /api/merchant/refunds/:id/approve
 * 商家审批售后申请
 */
async function reviewRefund(req, res) {
  try {
    const { id } = req.params;
    const { action, reason } = req.body;

    // 参数校验
    if (!action || !['approve', 'reject'].includes(action)) {
      return response.fail(res, 'action 参数无效，必须为 approve 或 reject', 400);
    }
    if (action === 'reject' && (!reason || !reason.trim())) {
      return response.fail(res, '拒绝时必须填写原因', 400);
    }

    const result = await refundService.approveRefund(
      req.userId,
      Number(id),
      action,
      reason || null
    );
    response.success(res, result, action === 'approve' ? '已同意售后申请' : '已拒绝售后申请');
  } catch (e) {
    switch (e.message) {
      case 'NOT_FOUND':
        return response.fail(res, '售后申请不存在', 404);
      case 'NOT_MERCHANT':
        return response.forbidden(res, '无权操作，非商家身份');
      case 'NOT_YOUR_REFUND':
      case 'NOT_YOUR_SHOP':
        return response.forbidden(res, '无权操作，该售后单不属于您的店铺');
      case 'ALREADY_REVIEWED':
      case 'INVALID_STATUS':
        return response.fail(res, '当前售后状态不允许此操作，请刷新后重试', 409);
      case 'EXCEED_AMOUNT':
        return response.fail(res, '退款金额不可超过实付金额', 422);
      default:
        return response.error(res, e.message || '审批操作失败');
    }
  }
}

module.exports = { listShopRefunds, reviewRefund };

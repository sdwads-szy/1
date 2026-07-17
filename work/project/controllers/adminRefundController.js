const adminRefundService = require('../services/adminRefundService');
const response = require('../utils/response');

/**
 * GET /api/admin/refunds/arbitration
 * 获取仲裁工单列表（仅 status=arbitrating）
 */
async function getArbitrationList(req, res) {
  try {
    const { page = 1, pageSize = 20, status, requestNo } = req.query;
    const result = await adminRefundService.getArbitrationList({
      page: parseInt(page) || 1,
      pageSize: parseInt(pageSize) || 20,
      status,
      requestNo
    });
    response.success(res, result);
  } catch (e) {
    response.error(res, e.message);
  }
}

/**
 * POST /api/admin/refunds/:id/arbitrate
 * 执行仲裁裁决：force_refund（强制退款）或 dismiss（驳回申请）
 */
async function arbitrateRefund(req, res) {
  try {
    const { id } = req.params;
    const { ruling, reason } = req.body;
    const adminId = req.userId;

    if (!ruling) {
      return response.fail(res, '缺少裁决结果 ruling', 400);
    }

    const result = await adminRefundService.arbitrateRefund(
      parseInt(id),
      { ruling, reason },
      adminId
    );

    const msg = ruling === 'force_refund' ? '已执行强制退款' : '已驳回仲裁申请';
    response.success(res, result, msg);
  } catch (e) {
    switch (e.message) {
      case 'NOT_FOUND':
        return response.fail(res, '售后申请不存在', 404);
      case 'INVALID_STATUS':
        return response.fail(res, '当前售后状态不可仲裁，请刷新后重试', 409);
      case 'INVALID_RULING':
        return response.fail(res, '无效的裁决结果，仅支持 force_refund / dismiss', 400);
      default:
        response.error(res, e.message);
    }
  }
}

module.exports = { getArbitrationList, arbitrateRefund };

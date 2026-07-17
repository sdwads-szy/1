const adminWithdrawalService = require('../services/adminWithdrawalService');
const response = require('../utils/response');

const errorMapping = {
  WITHDRAWAL_NOT_FOUND: { status: 404, message: '提现申请不存在' },
  ALREADY_PROCESSED: { status: 409, message: '该提现申请已处理' },
  MISSING_ID: { status: 400, message: '缺少提现申请ID' },
  MISSING_ACTION: { status: 400, message: '缺少审批动作' },
  INVALID_ACTION: { status: 400, message: '无效的审批动作，仅支持 approve/reject' },
  REJECT_REASON_REQUIRED: { status: 400, message: '驳回时必须填写原因' },
  CONFLICT: { status: 409, message: '数据已变动，请刷新重试' },
  WALLET_NOT_FOUND: { status: 404, message: '商家钱包不存在' },
  INSUFFICIENT_FROZEN: { status: 422, message: '冻结余额不足' },
};

/**
 * GET /api/admin/withdrawals
 * 平台管理员查看所有提现申请列表
 * @query page — 页码，默认1
 * @query pageSize — 每页条数，默认20
 * @query status — 状态筛选：pending/approved/paid/rejected
 * @query merchant_id — 商家ID筛选（可选）
 */
async function getWithdrawals(req, res) {
  try {
    const page = parseInt(req.query.page) || 1;
    const pageSize = parseInt(req.query.pageSize) || 20;
    const { status, merchant_id } = req.query;
    const merchantId = merchant_id ? parseInt(merchant_id) : undefined;

    const result = await adminWithdrawalService.getWithdrawals(page, pageSize, status, merchantId);
    response.success(res, result);
  } catch (e) {
    const mapped = errorMapping[e.message];
    if (mapped) return response.fail(res, mapped.message, mapped.status);
    response.error(res, '服务器内部错误');
  }
}

/**
 * POST /api/admin/withdrawals/:id/approve
 * 平台管理员审批提现申请（通过→打款扣冻结余额 / 驳回→返还余额）
 * @param id — 提现申请ID（路由参数）
 * @body action — 'approve' | 'reject'
 * @body reason — 驳回原因（reject时必填）
 */
async function approveWithdrawal(req, res) {
  try {
    const id = parseInt(req.params.id);
    const { action, reason } = req.body;
    const adminId = req.userId;

    if (!id || isNaN(id)) throw new Error('MISSING_ID');
    if (!action) throw new Error('MISSING_ACTION');
    if (!['approve', 'reject'].includes(action)) throw new Error('INVALID_ACTION');
    if (action === 'reject' && (!reason || reason.trim() === '')) throw new Error('REJECT_REASON_REQUIRED');

    const result = await adminWithdrawalService.approveWithdrawal(id, action, adminId, reason);
    response.success(res, result);
  } catch (e) {
    const mapped = errorMapping[e.message];
    if (mapped) return response.fail(res, mapped.message, mapped.status);
    response.error(res, '服务器内部错误');
  }
}

module.exports = { getWithdrawals, approveWithdrawal };

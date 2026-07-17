const adminSettlementService = require('../services/adminSettlementService');
const response = require('../utils/response');

const VALID_STATUSES = ['pending', 'confirmed', 'paid', 'completed', 'clawed_back'];

/**
 * GET /api/admin/settlements
 * 平台结算管理：查看所有商家结算单，支持状态筛选和分页
 */
async function listSettlements(req, res) {
  try {
    const { status, page: pageStr, pageSize: pageSizeStr } = req.query;
    const page = parseInt(pageStr) || 1;
    const pageSize = parseInt(pageSizeStr) || 20;

    // 校验分页参数
    if (page < 1) {
      return response.fail(res, '页码必须大于0', 400);
    }
    if (pageSize < 1 || pageSize > 50) {
      return response.fail(res, '每页数量需在1-50之间', 400);
    }

    // 校验状态筛选值
    if (status && !VALID_STATUSES.includes(status)) {
      return response.fail(res, '无效的结算状态', 400);
    }

    const result = await adminSettlementService.getSettlements(status || null, page, pageSize);
    response.success(res, result, '查询成功');
  } catch (e) {
    response.fail(res, e.message, 500);
  }
}

/**
 * POST /api/admin/settlements/:id/pay
 * 结算打款：校验结算单已确认 → 标记打款 → 钱包入账 → 审计日志
 */
async function paySettlement(req, res) {
  try {
    const settlementId = parseInt(req.params.id);
    if (!settlementId || settlementId < 1) {
      return response.fail(res, '无效的结算单ID', 400);
    }

    const adminId = req.userId;
    const result = await adminSettlementService.paySettlement(adminId, settlementId);
    response.success(res, result, '打款成功');
  } catch (e) {
    const errorMap = {
      FORBIDDEN: { status: 403, message: '无权限访问' },
      SETTLEMENT_NOT_FOUND: { status: 404, message: '结算单不存在' },
      SETTLEMENT_NOT_CONFIRMED: { status: 422, message: '结算单未确认，无法打款' },
      WALLET_NOT_FOUND: { status: 500, message: '商家钱包不存在，请联系技术支持' },
      WALLET_VERSION_CONFLICT: { status: 409, message: '钱包余额已变动，请刷新后重试' }
    };

    const mapped = errorMap[e.message];
    if (mapped) {
      response.fail(res, mapped.message, mapped.status);
    } else {
      response.fail(res, e.message, 500);
    }
  }
}

module.exports = { listSettlements, paySettlement };

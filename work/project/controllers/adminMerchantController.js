const response = require('../utils/response');
const adminMerchantService = require('../services/adminMerchantService');

/**
 * GET /api/admin/merchants
 * 平台商家列表：支持 status 筛选 + 分页
 */
async function listMerchants(req, res) {
  try {
    const { status } = req.query;
    const page = parseInt(req.query.page) || 1;
    const pageSize = parseInt(req.query.pageSize) || 20;

    // 校验 pageSize 上限
    const safePageSize = Math.min(Math.max(pageSize, 1), 50);
    const safePage = Math.max(page, 1);

    const result = await adminMerchantService.getMerchantsList(status, safePage, safePageSize);
    response.success(res, result);
  } catch (e) {
    response.fail(res, '查询商家列表失败', 500);
  }
}

/**
 * POST /api/admin/merchants/:id/review
 * 商家入驻审核：通过或驳回
 */
async function reviewMerchant(req, res) {
  try {
    const adminId = req.userId;
    const merchantId = parseInt(req.params.id);
    const { action, reason } = req.body;
    // 边界校验：已审核的申请不可重复审核
    const merchant = await adminMerchantService.getMerchantById(merchantId);
    if (!merchant || merchant.status !== 'pending_review') {
      return response.fail(res, '该申请已审核', 409);
    }

    // 驳回时 reason 必填
    if (action === 'reject' && !reason) {
      return response.fail(res, '驳回时必须填写审核意见', 400);
    }

    const result = await adminMerchantService.reviewMerchant(adminId, merchantId, action, reason || null);
    response.success(res, result, action === 'approve' ? '审核通过' : '已驳回');
  } catch (e) {
    const errorMap = {
      'FORBIDDEN': { status: 403, message: '无权限访问' },
      'MERCHANT_NOT_FOUND': { status: 404, message: '商家不存在' },
      'ALREADY_REVIEWED': { status: 409, message: '该商家已审核' },
    };
    const mapped = errorMap[e.message];
    if (mapped) {
      response.fail(res, mapped.message, mapped.status);
    } else {
      response.fail(res, '审核失败', 500);
    }
  }
}

/**
 * POST /api/admin/merchants/:id/freeze
 * 冻结/解冻商家：冻结时联动店铺+商品下架
 */
async function freezeMerchant(req, res) {
  try {
    const adminId = req.userId;
    const merchantId = parseInt(req.params.id);
    const { action } = req.body;

    const result = await adminMerchantService.freezeMerchant(adminId, merchantId, action);
    response.success(res, result, action === 'freeze' ? '已冻结' : '已解冻');
  } catch (e) {
    const errorMap = {
      'MERCHANT_NOT_FOUND': { status: 404, message: '商家不存在' },
      'INVALID_ACTION': { status: 422, message: '无效操作：商家当前状态不允许此操作' },
    };
    const mapped = errorMap[e.message];
    if (mapped) {
      response.fail(res, mapped.message, mapped.status);
    } else {
      response.fail(res, '操作失败', 500);
    }
  }
}

module.exports = { listMerchants, reviewMerchant, freezeMerchant };

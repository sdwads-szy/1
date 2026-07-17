const response = require('../utils/response');
const adminProductService = require('../services/adminProductService');

/**
 * GET /api/admin/products
 * 审核列表：按状态筛选商品，默认查询草稿状态
 */
async function listProducts(req, res) {
  try {
    const { status = 'draft', page = 1, pageSize = 20, keyword, dateRange } = req.query;
    const result = await adminProductService.listProducts(status, parseInt(page), parseInt(pageSize), keyword, dateRange);
    response.success(res, result);
  } catch (e) {
    response.error(res, e.message);
  }
}

/**
 * POST /api/admin/products/:id/review
 * 商品审核：通过上架 / 驳回回退
 */
async function reviewProduct(req, res) {
  try {
    const adminId = req.userId;
    const productId = parseInt(req.params.id);
    const { action, reason } = req.body;

    const result = await adminProductService.reviewProduct(adminId, productId, action, reason);
    response.success(res, result, '审核完成');
  } catch (e) {
    const errorMap = {
      'PRODUCT_NOT_FOUND': { status: 404, message: '商品不存在' },
      'INVALID_ACTION':     { status: 400, message: '无效的审核动作，仅支持 approve/reject' },
      'REASON_REQUIRED':    { status: 400, message: '驳回时必须填写原因' }
    };
    const mapped = errorMap[e.message];
    if (mapped) {
      response.fail(res, mapped.message, mapped.status);
    } else if (e.message === 'SENSITIVE_WORD') {
      const words = e.sensitiveWords || [];
      response.fail(res, `商品含敏感词：[${words.join(', ')}]`, 422);
    } else {
      response.error(res, e.message);
    }
  }
}

module.exports = { listProducts, reviewProduct };

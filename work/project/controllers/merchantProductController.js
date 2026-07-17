const response = require('../utils/response');
const merchantProductService = require('../services/merchantProductService');
const db = require('../config/db');

/**
 * 从 userId 查询商家 ID（merchants.id）
 * 商家必须审核通过（status='approved'）
 */
async function getMerchantId(userId) {
  const rows = await db.query(
    'SELECT id FROM merchants WHERE user_id = ? AND status = ?',
    [userId, 'approved']
  );
  if (!rows.length) throw new Error('SHOP_NOT_FOUND');
  return rows[0].id;
}

/**
 * GET /api/merchant/products
 * 商品列表：查看本店所有商品，支持状态筛选和分页
 */
async function getMerchantProducts(req, res) {
  try {
    const merchantId = await getMerchantId(req.userId);
    const { status, page, pageSize } = req.query;

    const result = await merchantProductService.listProducts(
      merchantId,
      status || null,
      parseInt(page) || 1,
      parseInt(pageSize) || 20
    );

    response.success(res, result, '获取成功');
  } catch (e) {
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在，请先完成入驻', 404);
    }
    response.error(res, e.message);
  }
}

/**
 * POST /api/merchant/products
 * 发布新商品：校验店铺状态 → 事务创建 SPU+SKU+库存+图片
 */
async function createMerchantProduct(req, res) {
  try {
    const merchantId = await getMerchantId(req.userId);
    const { categoryId, name, description, skus, images } = req.body;

    const result = await merchantProductService.publishProduct(
      merchantId,
      categoryId,
      name,
      description || '',
      skus,
      images || []
    );

    response.success(res, result, '发布成功');
  } catch (e) {
    const errorMap = {
      'SHOP_FROZEN':       [422, '店铺已冻结，无法发布商品'],
      'SKU_PRICE_INVALID': [422, 'SKU价格必须大于0'],
      'SHOP_NOT_FOUND':    [404, '店铺不存在，请先完成入驻'],
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped[1], mapped[0]);
    response.error(res, e.message);
  }
}

/**
 * PUT /api/merchant/products/:id
 * 编辑商品：更新 SPU 基本信息，可选全量替换 SKU 和图片
 */
async function updateMerchantProduct(req, res) {
  try {
    const merchantId = await getMerchantId(req.userId);
    const productId = parseInt(req.params.id);

    // 只收集请求中实际传入的字段
    const updates = {};
    if (req.body.categoryId !== undefined) updates.categoryId = req.body.categoryId;
    if (req.body.name !== undefined)       updates.name = req.body.name;
    if (req.body.description !== undefined) updates.description = req.body.description;
    if (req.body.skus !== undefined)       updates.skus = req.body.skus;
    if (req.body.images !== undefined)     updates.images = req.body.images;

    const result = await merchantProductService.updateProduct(merchantId, productId, updates);
    response.success(res, result, '更新成功');
  } catch (e) {
    const errorMap = {
      'PRODUCT_NOT_FOUND':  [404, '商品不存在'],
      'NOT_OWN_PRODUCT':    [403, '无权编辑他人商品'],
      'SHOP_FROZEN':        [422, '店铺已冻结，无法编辑商品'],
      'SKU_PRICE_INVALID':  [422, 'SKU价格必须大于0'],
      'SHOP_NOT_FOUND':     [404, '店铺不存在，请先完成入驻'],
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped[1], mapped[0]);
    response.error(res, e.message);
  }
}

module.exports = { getMerchantProducts, createMerchantProduct, updateMerchantProduct };

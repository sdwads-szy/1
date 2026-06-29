const productService = require('../services/productService');
const response = require('../utils/response');
const db = require('../config/db');

/**
 * 错误码 → HTTP 响应映射
 */
function handleError(res, err) {
  const map = {
    PRODUCT_NOT_FOUND:          { code: 404, message: '商品不存在' },
    SKU_OUT_OF_STOCK:           { code: 422, message: '该规格已售罄' },
    QUANTITY_EXCEED:            { code: 422, message: '单品数量不能超过99件' },
    SHOP_NOT_ACTIVE:            { code: 403, message: '店铺未激活，无法发布商品' },
    CATEGORY_INVALID:           { code: 422, message: '类目不存在或已禁用' },
    SKU_SPEC_DUPLICATE:         { code: 422, message: '存在重复的SKU规格组合' },
    SKU_REQUIRED:               { code: 400, message: '至少需要一个SKU' },
    SKU_INVALID:                { code: 400, message: 'SKU信息不完整' },
    SKU_PRICE_INVALID:          { code: 400, message: 'SKU价格不能为负数' },
    SKU_STOCK_INVALID:          { code: 400, message: 'SKU库存不能为负数' },
    ALREADY_REVIEWED:           { code: 409, message: '商品已审核' },
    PRODUCT_NOT_APPROVED:       { code: 422, message: '商品未审核通过，无法上架' },
    NOT_PRODUCT_OWNER:          { code: 403, message: '无权操作此商品' },
    PRODUCT_NOT_LISTED:         { code: 422, message: '商品未上架，无法下架' },
    PRODUCT_STATUS_NOT_EDITABLE:{ code: 422, message: '当前状态不允许编辑' },
    INVALID_REVIEW_RESULT:      { code: 400, message: '审核结果无效，必须为 approved 或 rejected' }
  };

  const entry = map[err.message];
  if (entry) {
    return response.fail(res, entry.message, entry.code);
  }
  return response.fail(res, '服务器内部错误', 500);
}

/**
 * 商家接口 — 通过 userId 查 shopId
 */
async function resolveShopId(userId) {
  const rows = await db.query(
    'SELECT id FROM shops WHERE user_id = ?',
    [userId]
  );
  if (!rows.length) {
    return null;
  }
  return rows[0].id;
}

/* ===== 前台接口 ===== */

/** GET /api/products */
exports.listProducts = async (req, res) => {
  try {
    const { categoryId, sort, page, pageSize, priceMin, priceMax } = req.query;
    const result = await productService.listProducts({
      categoryId: categoryId || undefined,
      sort: sort || undefined,
      page,
      pageSize,
      priceMin: priceMin || undefined,
      priceMax: priceMax || undefined
    });
    response.success(res, result, '获取商品列表成功');
  } catch (err) {
    handleError(res, err);
  }
};

/** GET /api/products/:id */
exports.getProductDetail = async (req, res) => {
  try {
    const result = await productService.getProductDetail(req.params.id);
    response.success(res, result, '获取商品详情成功');
  } catch (err) {
    handleError(res, err);
  }
};

/* ===== 商家接口 ===== */

/** GET /api/merchant/products */
exports.getMerchantProducts = async (req, res) => {
  try {
    const shopId = await resolveShopId(req.userId);
    if (!shopId) {
      return response.fail(res, '店铺不存在', 404);
    }
    const { status, page, pageSize } = req.query;
    const result = await productService.getMerchantProducts(shopId, { status, page, pageSize });
    response.success(res, result, '获取商品列表成功');
  } catch (err) {
    handleError(res, err);
  }
};

/** GET /api/merchant/products/:id */
exports.getMerchantProductDetail = async (req, res) => {
  try {
    const shopId = await resolveShopId(req.userId);
    if (!shopId) {
      return response.fail(res, '店铺不存在', 404);
    }
    const result = await productService.getMerchantProductDetail(req.params.id, shopId);
    response.success(res, result, '获取商品详情成功');
  } catch (err) {
    handleError(res, err);
  }
};

/** POST /api/merchant/products */
exports.createProduct = async (req, res) => {
  try {
    const shopId = await resolveShopId(req.userId);
    if (!shopId) {
      return response.fail(res, '店铺不存在', 404);
    }

    const { categoryId, title, description, mainImage, skus } = req.body;
    if (!title || !title.trim()) {
      return response.fail(res, '商品标题不能为空', 400);
    }
    if (!skus || !Array.isArray(skus) || !skus.length) {
      return response.fail(res, '至少需要一个SKU', 400);
    }

    const result = await productService.createProduct(shopId, {
      categoryId,
      title: title.trim(),
      description,
      mainImage,
      skus
    });
    response.success(res, result, '商品发布成功，等待审核');
  } catch (err) {
    handleError(res, err);
  }
};

/** PUT /api/merchant/products/:id */
exports.updateProduct = async (req, res) => {
  try {
    const shopId = await resolveShopId(req.userId);
    if (!shopId) {
      return response.fail(res, '店铺不存在', 404);
    }
    const { categoryId, title, description, mainImage, skus } = req.body;
    const result = await productService.updateProduct(req.params.id, shopId, {
      categoryId,
      title,
      description,
      mainImage,
      skus
    });
    response.success(res, result, '商品更新成功');
  } catch (err) {
    handleError(res, err);
  }
};

/** PUT /api/merchant/products/:id/list */
exports.listProduct = async (req, res) => {
  try {
    const shopId = await resolveShopId(req.userId);
    if (!shopId) {
      return response.fail(res, '店铺不存在', 404);
    }
    const result = await productService.listProduct(req.params.id, shopId);
    response.success(res, result, '商品上架成功');
  } catch (err) {
    handleError(res, err);
  }
};

/** PUT /api/merchant/products/:id/delist */
exports.delistProduct = async (req, res) => {
  try {
    const shopId = await resolveShopId(req.userId);
    if (!shopId) {
      return response.fail(res, '店铺不存在', 404);
    }
    const result = await productService.delistProduct(req.params.id, shopId);
    response.success(res, result, '商品下架成功');
  } catch (err) {
    handleError(res, err);
  }
};

/* ===== 管理员接口 ===== */

/** GET /api/admin/products */
exports.getAdminProducts = async (req, res) => {
  try {
    const { status, page, pageSize } = req.query;
    const result = await productService.getAdminProducts({ status, page, pageSize });
    response.success(res, result, '获取审核列表成功');
  } catch (err) {
    handleError(res, err);
  }
};

/** GET /api/admin/products/:id */
exports.getAdminProductDetail = async (req, res) => {
  try {
    const result = await productService.getAdminProductDetail(req.params.id);
    response.success(res, result, '获取审核详情成功');
  } catch (err) {
    handleError(res, err);
  }
};

/** PUT /api/admin/products/:id/review */
exports.reviewProduct = async (req, res) => {
  try {
    const { result, reason } = req.body;
    if (!result) {
      return response.fail(res, '审核结果不能为空', 400);
    }
    const data = await productService.reviewProduct(req.params.id, req.userId, { result, reason });
    response.success(res, data, result === 'approved' ? '审核通过' : '已驳回');
  } catch (err) {
    handleError(res, err);
  }
};

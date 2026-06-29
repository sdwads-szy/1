const response = require('../utils/response');
const logger = require('../config/logger');
const service = require('../services/merchantService');

// ==================== 商家端 ====================

/**
 * POST /api/merchant/register — 商家注册
 */
async function register(req, res) {
  try {
    const { phone, verifyCode, password } = req.body;

    if (!phone || !verifyCode || !password) {
      return response.fail(res, '手机号、验证码和密码不能为空', 400);
    }
    if (typeof password !== 'string' || password.length < 6) {
      return response.fail(res, '密码至少6位', 400);
    }

    const result = await service.registerMerchant(phone, verifyCode, password);
    return response.success(res, result, '注册成功');
  } catch (e) {
    logger.error('register error:', e.message);
    const errorMap = {
      INVALID_PHONE: { msg: '手机号格式不正确', code: 400 },
      VERIFY_CODE_WRONG: { msg: '验证码错误', code: 400 },
      PHONE_REGISTERED: { msg: '该手机号已注册', code: 409 }
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped.msg, mapped.code);
    return response.error(res, '注册失败，请稍后重试');
  }
}

/**
 * POST /api/merchant/qualifications — 提交资质
 */
async function submitQualification(req, res) {
  try {
    const { businessLicense, legalPersonId, bankAccount } = req.body;

    if (!businessLicense || !legalPersonId || !bankAccount) {
      return response.fail(res, '营业执照、法人身份证和银行账户不能为空', 400);
    }

    const result = await service.submitQualification(req.userId, businessLicense, legalPersonId, bankAccount);
    return response.success(res, result, '资质提交成功');
  } catch (e) {
    logger.error('submitQualification error:', e.message);
    const errorMap = {
      SHOP_NOT_FOUND: { msg: '店铺不存在', code: 404 },
      ALREADY_SUBMITTED: { msg: '已提交资质审核，请勿重复提交', code: 409 },
      OCR_FAIL: { msg: '资质图片识别失败，请重新上传清晰图片', code: 422 }
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped.msg, mapped.code);
    return response.error(res, '提交失败，请稍后重试');
  }
}

/**
 * GET /api/merchant/shop — 获取店铺信息
 */
async function getShop(req, res) {
  try {
    const shop = await service.getShop(req.userId);
    return response.success(res, shop, '获取店铺信息成功');
  } catch (e) {
    logger.error('getShop error:', e.message);
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    return response.error(res, '获取店铺信息失败');
  }
}

/**
 * PUT /api/merchant/shop — 更新店铺信息
 */
async function updateShop(req, res) {
  try {
    const { name, logo, description } = req.body;

    if (name !== undefined && (typeof name !== 'string' || name.trim().length === 0)) {
      return response.fail(res, '店铺名称不能为空', 400);
    }

    await service.updateShop(req.userId, { name, logo, description });
    return response.success(res, { success: true }, '店铺信息更新成功');
  } catch (e) {
    logger.error('updateShop error:', e.message);
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    return response.error(res, '更新店铺信息失败');
  }
}

/**
 * GET /api/merchant/products — 商家商品列表
 */
async function getProducts(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const p = parseInt(page) || 1;
    const ps = Math.min(parseInt(pageSize) || 20, 100);

    const result = await service.getMerchantProducts(req.userId, { status, page: p, pageSize: ps });
    return response.success(res, result, '获取商品列表成功');
  } catch (e) {
    logger.error('getProducts error:', e.message);
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    return response.error(res, '获取商品列表失败');
  }
}

/**
 * POST /api/merchant/products — 发布商品
 */
async function createProduct(req, res) {
  try {
    const { categoryId, title, description, mainImage, skus } = req.body;

    if (!categoryId) return response.fail(res, '请选择类目', 400);
    if (!title || typeof title !== 'string' || title.trim().length === 0) {
      return response.fail(res, '商品标题不能为空', 400);
    }
    if (!skus || !Array.isArray(skus) || skus.length === 0) {
      return response.fail(res, '至少需要一个SKU', 400);
    }
    for (const sku of skus) {
      if (!sku.price || parseFloat(sku.price) <= 0) {
        return response.fail(res, 'SKU价格必须大于0', 400);
      }
    }

    const result = await service.createProduct(req.userId, { categoryId, title, description, mainImage, skus });
    return response.success(res, result, '商品发布成功');
  } catch (e) {
    logger.error('createProduct error:', e.message);
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    return response.error(res, '商品发布失败');
  }
}

/**
 * GET /api/merchant/products/:id — 商品详情
 */
async function getProductById(req, res) {
  try {
    const productId = parseInt(req.params.id) || 0;
    if (!productId) return response.fail(res, '无效的商品ID', 400);

    const result = await service.getMerchantProductById(req.userId, productId);
    return response.success(res, result, '获取商品详情成功');
  } catch (e) {
    logger.error('getProductById error:', e.message);
    const errorMap = {
      SHOP_NOT_FOUND: { msg: '店铺不存在', code: 404 },
      PRODUCT_NOT_FOUND: { msg: '商品不存在', code: 404 }
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped.msg, mapped.code);
    return response.error(res, '获取商品详情失败');
  }
}

/**
 * PUT /api/merchant/products/:id — 编辑商品
 */
async function updateProduct(req, res) {
  try {
    const productId = parseInt(req.params.id) || 0;
    if (!productId) return response.fail(res, '无效的商品ID', 400);

    const { categoryId, title, description, mainImage, skus } = req.body;

    await service.updateMerchantProduct(req.userId, productId, { categoryId, title, description, mainImage, skus });
    return response.success(res, { success: true }, '商品更新成功');
  } catch (e) {
    logger.error('updateProduct error:', e.message);
    const errorMap = {
      SHOP_NOT_FOUND: { msg: '店铺不存在', code: 404 },
      PRODUCT_NOT_FOUND: { msg: '商品不存在', code: 404 }
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped.msg, mapped.code);
    return response.error(res, '商品更新失败');
  }
}

/**
 * PUT /api/merchant/products/:id/list — 上架商品
 */
async function listProduct(req, res) {
  try {
    const productId = parseInt(req.params.id) || 0;
    if (!productId) return response.fail(res, '无效的商品ID', 400);

    await service.listProduct(req.userId, productId);
    return response.success(res, { success: true }, '上架成功');
  } catch (e) {
    logger.error('listProduct error:', e.message);
    const errorMap = {
      SHOP_NOT_FOUND: { msg: '店铺不存在', code: 404 },
      PRODUCT_NOT_FOUND: { msg: '商品不存在', code: 404 }
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped.msg, mapped.code);
    return response.error(res, '上架失败');
  }
}

/**
 * PUT /api/merchant/products/:id/delist — 下架商品
 */
async function delistProduct(req, res) {
  try {
    const productId = parseInt(req.params.id) || 0;
    if (!productId) return response.fail(res, '无效的商品ID', 400);

    await service.delistProduct(req.userId, productId);
    return response.success(res, { success: true }, '下架成功');
  } catch (e) {
    logger.error('delistProduct error:', e.message);
    const errorMap = {
      SHOP_NOT_FOUND: { msg: '店铺不存在', code: 404 },
      PRODUCT_NOT_FOUND: { msg: '商品不存在', code: 404 }
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped.msg, mapped.code);
    return response.error(res, '下架失败');
  }
}

/**
 * GET /api/merchant/orders — 商家订单列表
 */
async function getOrders(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const p = parseInt(page) || 1;
    const ps = Math.min(parseInt(pageSize) || 20, 100);

    const result = await service.getMerchantOrders(req.userId, { status, page: p, pageSize: ps });
    return response.success(res, result, '获取订单列表成功');
  } catch (e) {
    logger.error('getOrders error:', e.message);
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    return response.error(res, '获取订单列表失败');
  }
}

/**
 * GET /api/merchant/refunds — 商家退款列表
 */
async function getRefunds(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const p = parseInt(page) || 1;
    const ps = Math.min(parseInt(pageSize) || 20, 100);

    const result = await service.getMerchantRefunds(req.userId, { status, page: p, pageSize: ps });
    return response.success(res, result, '获取退款列表成功');
  } catch (e) {
    logger.error('getRefunds error:', e.message);
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    return response.error(res, '获取退款列表失败');
  }
}

// ==================== 平台后台 ====================

/**
 * GET /api/admin/merchants — 商家列表（平台审核）
 */
async function getAdminMerchants(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const p = parseInt(page) || 1;
    const ps = Math.min(parseInt(pageSize) || 20, 100);

    const result = await service.getAdminMerchants({ status, page: p, pageSize: ps });
    return response.success(res, result, '获取商家列表成功');
  } catch (e) {
    logger.error('getAdminMerchants error:', e.message);
    return response.error(res, '获取商家列表失败');
  }
}

/**
 * GET /api/admin/merchants/:id — 商家详情
 */
async function getAdminMerchantDetail(req, res) {
  try {
    const shopId = parseInt(req.params.id) || 0;
    if (!shopId) return response.fail(res, '无效的商家ID', 400);

    const result = await service.getAdminMerchantDetail(shopId);
    return response.success(res, result, '获取商家详情成功');
  } catch (e) {
    logger.error('getAdminMerchantDetail error:', e.message);
    if (e.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '商家不存在', 404);
    }
    return response.error(res, '获取商家详情失败');
  }
}

/**
 * PUT /api/admin/merchants/:id/review — 审核商家资质
 */
async function reviewMerchant(req, res) {
  try {
    const shopId = parseInt(req.params.id) || 0;
    if (!shopId) return response.fail(res, '无效的商家ID', 400);

    const { result, note } = req.body;
    if (!result || !['approved', 'rejected'].includes(result)) {
      return response.fail(res, '审核结果必须为 approved 或 rejected', 400);
    }

    const reviewResult = await service.reviewQualification(shopId, req.userId, result, note);
    return response.success(res, reviewResult, '审核完成');
  } catch (e) {
    logger.error('reviewMerchant error:', e.message);
    const errorMap = {
      QUALIFICATION_NOT_FOUND: { msg: '资质记录不存在', code: 404 },
      ALREADY_REVIEWED: { msg: '资质已审核', code: 409 }
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped.msg, mapped.code);
    return response.error(res, '审核失败');
  }
}

/**
 * PUT /api/admin/merchants/:id/activate — 激活店铺
 */
async function activateMerchant(req, res) {
  try {
    const shopId = parseInt(req.params.id) || 0;
    if (!shopId) return response.fail(res, '无效的商家ID', 400);

    const result = await service.activateShop(shopId);
    return response.success(res, result, '店铺激活成功');
  } catch (e) {
    logger.error('activateMerchant error:', e.message);
    const errorMap = {
      SHOP_NOT_FOUND: { msg: '店铺不存在', code: 404 },
      QUALIFICATION_NOT_APPROVED: { msg: '资质未审核通过，无法激活店铺', code: 422 }
    };
    const mapped = errorMap[e.message];
    if (mapped) return response.fail(res, mapped.msg, mapped.code);
    return response.error(res, '激活失败');
  }
}

module.exports = {
  register,
  submitQualification,
  getShop,
  updateShop,
  getProducts,
  createProduct,
  getProductById,
  updateProduct,
  listProduct,
  delistProduct,
  getOrders,
  getRefunds,
  getAdminMerchants,
  getAdminMerchantDetail,
  reviewMerchant,
  activateMerchant
};

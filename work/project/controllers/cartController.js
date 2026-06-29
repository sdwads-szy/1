const cartService = require('../services/cartService');
const response = require('../utils/response');

/**
 * 获取购物车列表
 * GET /api/cart
 */
exports.getCart = async (req, res, next) => {
  try {
    const result = await cartService.getCartItems(req.userId);
    response.success(res, result, '获取购物车成功');
  } catch (e) {
    next(e);
  }
};

/**
 * 加入购物车
 * POST /api/cart
 */
exports.addToCart = async (req, res, next) => {
  try {
    const { skuId, quantity } = req.body;

    if (!skuId || !quantity || parseInt(quantity) < 1) {
      return response.fail(res, '参数错误', 400);
    }

    const result = await cartService.addToCart(req.userId, skuId, quantity);
    response.success(res, result, '加入购物车成功');
  } catch (e) {
    if (e.message === 'PRODUCT_NOT_FOUND') return response.fail(res, '商品不存在', 404);
    if (e.message === 'SKU_OUT_OF_STOCK') return response.fail(res, '该规格已售罄', 422);
    if (e.message === 'QUANTITY_EXCEED') return response.fail(res, '单品数量不能超过99件', 422);
    next(e);
  }
};

/**
 * 更新购物车商品数量
 * PUT /api/cart/:cartId
 */
exports.updateCartItem = async (req, res, next) => {
  try {
    const cartId = parseInt(req.params.cartId) || 0;
    const { quantity } = req.body;

    if (!cartId || !quantity || parseInt(quantity) < 1) {
      return response.fail(res, '参数错误', 400);
    }

    await cartService.updateQuantity(cartId, req.userId, quantity);
    response.success(res, { success: true }, '更新成功');
  } catch (e) {
    if (e.message === 'NOT_FOUND') return response.fail(res, '购物车记录不存在', 404);
    if (e.message === 'FORBIDDEN') return response.fail(res, '无权操作', 403);
    if (e.message === 'SKU_OUT_OF_STOCK') return response.fail(res, '该规格已售罄', 422);
    if (e.message === 'QUANTITY_EXCEED') return response.fail(res, '单品数量不能超过99件', 422);
    next(e);
  }
};

/**
 * 删除购物车商品
 * DELETE /api/cart/:cartId
 */
exports.removeCartItem = async (req, res, next) => {
  try {
    const cartId = parseInt(req.params.cartId) || 0;
    if (!cartId) {
      return response.fail(res, '参数错误', 400);
    }

    await cartService.removeItem(cartId, req.userId);
    response.success(res, { success: true }, '删除成功');
  } catch (e) {
    if (e.message === 'NOT_FOUND') return response.fail(res, '购物车记录不存在', 404);
    if (e.message === 'FORBIDDEN') return response.fail(res, '无权操作', 403);
    next(e);
  }
};

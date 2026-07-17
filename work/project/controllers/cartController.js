const cartService = require('../services/cartService');
const response = require('../utils/response');

/**
 * GET /api/cart — 获取当前用户的购物车列表（按店铺分组）
 */
async function getCart(req, res) {
  try {
    const cartData = await cartService.getCart(req.userId);
    response.success(res, cartData, '获取购物车成功');
  } catch (e) {
    const errorMap = {
      'SHOP_FROZEN': 422,
      'SPU_DELISTED': 422,
      'STOCK_INSUFFICIENT': 422,
      'UNAUTHORIZED': 401,
    };
    const status = errorMap[e.message] || 500;
    response.fail(res, e.message, status);
  }
}

/**
 * POST /api/cart — 添加商品到购物车
 * body: { skuId, quantity, shopId }
 */
async function addToCart(req, res) {
  try {
    const { skuId, quantity, shopId } = req.body;

    // 参数校验
    if (!skuId || !Number.isFinite(skuId) || skuId < 1) {
      return response.fail(res, '请选择商品规格', 400);
    }
    if (!quantity || !Number.isFinite(quantity) || quantity < 1) {
      return response.fail(res, '商品数量至少为1', 400);
    }
    if (!shopId || !Number.isFinite(shopId) || shopId < 1) {
      return response.fail(res, '店铺信息缺失', 400);
    }

    const result = await cartService.addToCart(req.userId, skuId, quantity, shopId);
    response.success(res, result, '已加入购物车');
  } catch (e) {
    const errorMap = {
      'SKU_NOT_FOUND': 404,
      'SKU_NOT_BELONG_TO_SHOP': 422,
      'SPU_NOT_LISTED': 422,
      'SHOP_NOT_OPEN': 422,
      'STOCK_INSUFFICIENT': 422,
      'UNAUTHORIZED': 401,
    };
    const status = errorMap[e.message] || 500;
    const messages = {
      'SKU_NOT_FOUND': '商品规格不存在',
      'SKU_NOT_BELONG_TO_SHOP': '商品不属于该店铺',
      'SPU_NOT_LISTED': '商品已下架，无法加入购物车',
      'SHOP_NOT_OPEN': '店铺已暂停营业',
      'STOCK_INSUFFICIENT': '商品库存不足',
    };
    response.fail(res, messages[e.message] || e.message, status);
  }
}

/**
 * PUT /api/cart/:id — 修改购物车商品数量
 * body: { quantity }
 */
async function updateCartItem(req, res) {
  try {
    const cartItemId = parseInt(req.params.id, 10);
    const { quantity } = req.body;

    if (!Number.isFinite(cartItemId) || cartItemId < 1) {
      return response.fail(res, '购物车项ID无效', 400);
    }
    if (!quantity || !Number.isFinite(quantity) || quantity < 1) {
      return response.fail(res, '商品数量至少为1', 400);
    }

    const result = await cartService.updateCartItem(req.userId, cartItemId, quantity);
    response.success(res, result, '数量已更新');
  } catch (e) {
    const errorMap = {
      'CART_ITEM_NOT_FOUND': 404,
      'STOCK_INSUFFICIENT': 422,
      'UNAUTHORIZED': 401,
    };
    const status = errorMap[e.message] || 500;
    const messages = {
      'CART_ITEM_NOT_FOUND': '购物车项不存在',
      'STOCK_INSUFFICIENT': '库存不足，无法设置该数量',
    };
    response.fail(res, messages[e.message] || e.message, status);
  }
}

/**
 * DELETE /api/cart/:id — 删除购物车单品
 */
async function removeCartItem(req, res) {
  try {
    const cartItemId = parseInt(req.params.id, 10);

    if (!Number.isFinite(cartItemId) || cartItemId < 1) {
      return response.fail(res, '购物车项ID无效', 400);
    }

    await cartService.removeCartItem(req.userId, cartItemId);
    response.success(res, null, '已从购物车移除');
  } catch (e) {
    const errorMap = {
      'CART_ITEM_NOT_FOUND': 404,
      'UNAUTHORIZED': 401,
    };
    const status = errorMap[e.message] || 500;
    const messages = {
      'CART_ITEM_NOT_FOUND': '购物车项不存在',
    };
    response.fail(res, messages[e.message] || e.message, status);
  }
}

/**
 * POST /api/cart/select — 选中购物车项准备结算
 * body: { cartItemIds: number[] }
 */
async function selectForCheckout(req, res) {
  try {
    const { cartItemIds } = req.body;

    if (!Array.isArray(cartItemIds) || cartItemIds.length === 0) {
      return response.fail(res, '请选择购物车项', 400);
    }

    const result = await cartService.selectForCheckout(req.userId, cartItemIds);
    response.success(res, result, '已选中');
  } catch (e) {
    const errorMap = {
      'STOCK_INSUFFICIENT': 422,
      'UNAUTHORIZED': 401,
    };
    const status = errorMap[e.message] || 500;
    response.fail(res, e.message, status);
  }
}

/**
 * PATCH /api/cart/batch-check — 批量勾选/取消勾选
 * body: { cartItemIds: number[], checked: boolean }
 */
async function batchCheck(req, res) {
  try {
    const { cartItemIds, checked } = req.body;

    if (!Array.isArray(cartItemIds) || cartItemIds.length === 0) {
      return response.fail(res, '请选择要操作的购物车项', 400);
    }
    if (typeof checked !== 'boolean') {
      return response.fail(res, '勾选状态无效', 400);
    }

    // 校验所有 ID 为正整数
    for (const id of cartItemIds) {
      if (!Number.isFinite(id) || id < 1) {
        return response.fail(res, '购物车项ID无效', 400);
      }
    }

    const result = await cartService.batchCheck(req.userId, cartItemIds, checked);
    response.success(res, result, checked ? '已勾选' : '已取消勾选');
  } catch (e) {
    const errorMap = {
      'UNAUTHORIZED': 401,
    };
    const status = errorMap[e.message] || 500;
    response.fail(res, e.message, status);
  }
}

/**
 * DELETE /api/cart — 清空购物车
 */
async function clearCart(req, res) {
  try {
    await cartService.clearCart(req.userId);
    response.success(res, null, '购物车已清空');
  } catch (e) {
    const errorMap = {
      'UNAUTHORIZED': 401,
    };
    const status = errorMap[e.message] || 500;
    response.fail(res, e.message, status);
  }
}

module.exports = {
  getCart,
  addToCart,
  updateCartItem,
  removeCartItem,
  selectForCheckout,
  batchCheck,
  clearCart,
};

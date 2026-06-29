import request from '@/utils/request';

/**
 * @api 购物车模块 — 加购/列表/修改数量/删除
 */

/** 获取购物车列表 */
export function getCartList() {
  return request({ url: '/cart', method: 'get' });
}

/** 添加商品到购物车 */
export function addToCart(data) {
  return request({ url: '/cart', method: 'post', data });
}

/** 修改购物车商品数量 */
export function updateCartItem(cartId, data) {
  return request({ url: `/cart/${cartId}`, method: 'put', data });
}

/** 删除购物车商品 */
export function deleteCartItem(cartId) {
  return request({ url: `/cart/${cartId}`, method: 'delete' });
}

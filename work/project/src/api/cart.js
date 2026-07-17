import request from '@/utils/request';

/**
 * 获取购物车列表 — 按店铺分组返回当前用户购物车全部商品
 * @returns {Promise} { data: { groups: [{ shopId, shopName, items: [...] }] } }
 */
export function getCart() {
  return request({
    url: '/cart',
    method: 'get'
  });
}

/**
 * 加入购物车 — 添加商品或修改已有商品数量
 * @param {Object} data - { skuId: int, quantity: int, shopId: int }
 * @returns {Promise}
 */
export function addToCart(data) {
  return request({
    url: '/cart',
    method: 'post',
    data
  });
}

/**
 * 选中购物车项准备结算
 * @param {Object} data - { cartItemIds: int[] }
 * @returns {Promise}
 */
export function selectForCheckout(data) {
  return request({
    url: '/cart/select',
    method: 'post',
    data
  });
}

/**
 * 批量勾选/取消勾选 — 结算前校验库存和店铺状态
 * @param {Object} data - { cartItemIds: int[], checked: boolean }
 * @returns {Promise} { data: { unavailableItems: [...] } }
 */
export function batchCheckCart(data) {
  return request({
    url: '/cart/batch-check',
    method: 'patch',
    data
  });
}

import request from '@/utils/request';

/**
 * @api 商家商品管理 — 列表/发布/编辑
 */

/**
 * 获取商家商品列表
 * @param {Object} data - { status?, page?, pageSize? }
 * @returns {Promise}
 */
export function getMerchantProducts(data) {
  return request({ url: '/merchant/products', method: 'get', params: data });
}

/**
 * 创建新商品（SPU + SKU + 图片）
 * @param {Object} data - { categoryId, name, description, skus, images }
 * @returns {Promise}
 */
export function createMerchantProduct(data) {
  return request({ url: '/merchant/products', method: 'post', data });
}

/**
 * 更新商品信息
 * @param {Object} data - { id, categoryId?, name?, description?, skus?, images? }
 * @returns {Promise}
 */
export function updateMerchantProduct(data) {
  return request({ url: `/merchant/products/${data.id}`, method: 'put', data });
}

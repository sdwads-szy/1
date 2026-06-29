// @api 搜索模块 — 关键词搜索/联想建议
import request from '@/utils/request';

/**
 * 关键词搜索商品
 * @param {Object} data - { q, categoryId?, priceMin?, priceMax?, sort?, page, pageSize }
 * @returns {Promise<{ products: Array, total: number, suggestions: Array }>}
 */
export function searchProducts(data) {
  return request({ url: '/search/', method: 'get', params: data });
}

/**
 * 搜索联想建议
 * @param {Object} data - { q }
 * @returns {Promise<Array<{ text: string, type: 'history'|'hot'|'suggestion' }>>}
 */
export function getSuggestions(data) {
  return request({ url: '/search/suggestions', method: 'get', params: data });
}

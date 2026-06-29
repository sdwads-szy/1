// @api 商品接口：前台商品列表/详情
import request from '@/utils/request';

/**
 * 获取商品列表
 * @param {Object} data - { categoryId, sort, page, pageSize, priceMin, priceMax }
 * @returns {Promise}
 */
export function getProductList(data) {
  return request({
    url: '/products',
    method: 'get',
    params: data
  });
}

/**
 * 获取商品详情
 * @param {Object} data - { id }
 * @returns {Promise}
 */
export function getProductDetail(data) {
  return request({
    url: `/products/${data.id}`,
    method: 'get'
  });
}

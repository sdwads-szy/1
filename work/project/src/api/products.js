import request from '@/utils/request';

/**
 * 商品列表：支持关键词搜索、类目筛选、排序、分页
 * @param {Object} data - { q, cat, sort, page, pageSize }
 * @returns {Promise}
 */
export function getProducts(data) {
  return request({
    url: '/products',
    method: 'get',
    params: data
  });
}

/**
 * 商品详情：返回SPU信息、SKU列表、店铺信息、轮播图
 * @param {Object} data - { id }
 * @returns {Promise}
 */
export function getProductDetail(data) {
  return request({
    url: `/products/${data.id}`,
    method: 'get'
  });
}

/**
 * 获取全量类目树，用于首页分类导航和商品筛选
 * @returns {Promise}
 */
export function getCategories() {
  return request({
    url: '/categories',
    method: 'get'
  });
}

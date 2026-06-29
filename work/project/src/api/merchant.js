// @api 商家端接口模块
import request from '@/utils/request';

const BASE = '/merchant';

/** 商家注册 */
export function register(data) {
  return request({ url: `${BASE}/register`, method: 'post', data });
}

/** 提交资质审核 */
export function submitQualification(data) {
  return request({ url: `${BASE}/qualifications`, method: 'post', data });
}

/** 获取店铺信息 */
export function getShop() {
  return request({ url: `${BASE}/shop`, method: 'get' });
}

/** 更新店铺信息 */
export function updateShop(data) {
  return request({ url: `${BASE}/shop`, method: 'put', data });
}

/** 获取商品列表 */
export function getProductList(params) {
  return request({ url: `${BASE}/products`, method: 'get', params });
}

/** 获取单个商品详情 */
export function getProduct(id) {
  return request({ url: `${BASE}/products/${id}`, method: 'get' });
}

/** 发布/创建商品 */
export function createProduct(data) {
  return request({ url: `${BASE}/products`, method: 'post', data });
}

/** 更新商品 */
export function updateProduct(id, data) {
  return request({ url: `${BASE}/products/${id}`, method: 'put', data });
}

/** 上架商品 */
export function listProduct(id) {
  return request({ url: `${BASE}/products/${id}/list`, method: 'put' });
}

/** 下架商品 */
export function delistProduct(id) {
  return request({ url: `${BASE}/products/${id}/delist`, method: 'put' });
}

/** 获取商家订单列表 */
export function getOrderList(params) {
  return request({ url: `${BASE}/orders`, method: 'get', params });
}

/** 获取商家退款列表 */
export function getRefundList(params) {
  return request({ url: `${BASE}/refunds`, method: 'get', params });
}

import request from '@/utils/request';

/**
 * @api 平台商家管理
 * 获取平台商家列表，支持状态筛选与分页
 * @param {Object} data - { status?, page?, pageSize? }
 * @returns {Promise}
 */
export function getAdminMerchants(data) {
  return request({ url: '/admin/merchants', method: 'get', params: data });
}

/**
 * @api 平台商家管理
 * 商家入驻审核：通过或驳回入驻申请
 * @param {Object} data - { id, action, reason? }
 * @returns {Promise}
 */
export function reviewMerchant(data) {
  const { id, ...body } = data;
  return request({ url: `/admin/merchants/${id}/review`, method: 'post', data: body });
}

/**
 * @api 平台商家管理
 * 冻结/解冻商家：冻结后关联店铺商品立即下架
 * @param {Object} data - { id, action }
 * @returns {Promise}
 */
export function freezeMerchant(data) {
  const { id, ...body } = data;
  return request({ url: `/admin/merchants/${id}/freeze`, method: 'post', data: body });
}

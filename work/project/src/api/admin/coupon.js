import request from '@/utils/request';

/**
 * @api 平台后台优惠券管理
 * 提供优惠券列表查询、创建、发放功能
 */

/**
 * 获取优惠券列表
 * @param {Object} params - { status?, page, pageSize }
 * @returns {Promise<{ list: Array, total: number }>}
 */
export function getCouponList(params) {
  return request({
    url: '/admin/coupons',
    method: 'get',
    params
  });
}

/**
 * 创建优惠券
 * @param {Object} data - { title, amount, minOrder, validFrom, validTo }
 * @returns {Promise<{ couponId: number }>}
 */
export function createCoupon(data) {
  return request({
    url: '/admin/coupons',
    method: 'post',
    data
  });
}

/**
 * 发放优惠券（向指定用户或全量用户发放）
 * @param {number} id - 优惠券ID
 * @param {Object} data - { userIds: number[] } 空数组表示全场发放
 * @returns {Promise<{ grantedCount: number }>}
 */
export function grantCoupon(id, data) {
  return request({
    url: `/admin/coupons/${id}/grant`,
    method: 'post',
    data
  });
}

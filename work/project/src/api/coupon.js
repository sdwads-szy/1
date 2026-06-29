import request from '@/utils/request';

// @api 优惠券接口 — 券列表/领取/我的可用券

/**
 * 获取可领取的优惠券列表
 * @returns {Promise} { list: [{ id, title, amount, minOrder, validFrom, validTo }] }
 */
export function getCouponList() {
  return request({ url: '/coupons', method: 'get' });
}

/**
 * 领取优惠券
 * @param {number} id — 优惠券ID
 * @returns {Promise} { success }
 */
export function claimCoupon(id) {
  return request({ url: `/coupons/${id}/claim`, method: 'post' });
}

/**
 * 获取我的可用优惠券
 * @param {Object} params — { orderAmount? }
 * @returns {Promise} { list: [{ id, couponId, title, amount, minOrder }] }
 */
export function getMyCoupons(params) {
  return request({ url: '/coupons/my', method: 'get', params });
}

const couponService = require('../services/couponService');
const response = require('../utils/response');

/**
 * GET /api/coupons — 可领券列表（公开）
 */
async function listAvailableCoupons(req, res) {
  try {
    const coupons = await couponService.listAvailableCoupons();
    response.success(res, { list: coupons });
  } catch (e) {
    response.fail(res, '获取优惠券列表失败', 500);
  }
}

/**
 * POST /api/coupons/:id/claim — 领取优惠券
 */
async function claimCoupon(req, res) {
  try {
    const userId = req.userId;
    const couponId = parseInt(req.params.id) || 0;

    if (!couponId) {
      return response.fail(res, '无效的优惠券ID', 400);
    }

    const result = await couponService.claimCoupon(userId, couponId);
    response.success(res, result, '领取成功');
  } catch (e) {
    const errorMap = {
      'COUPON_NOT_FOUND': [404, '优惠券不存在'],
      'ALREADY_CLAIMED': [409, '已领取过该优惠券'],
      'COUPON_EXPIRED': [422, '优惠券已过期']
    };
    const [status, msg] = errorMap[e.message] || [500, '领取失败'];
    response.fail(res, msg, status);
  }
}

/**
 * GET /api/coupons/my — 我的可用券列表
 */
async function getMyCoupons(req, res) {
  try {
    const userId = req.userId;
    const orderAmount = req.query.orderAmount !== undefined
      ? parseFloat(req.query.orderAmount)
      : undefined;

    const coupons = await couponService.getMyCoupons(userId, orderAmount);
    response.success(res, { list: coupons });
  } catch (e) {
    response.fail(res, '获取我的优惠券失败', 500);
  }
}

// ==================== Admin controllers ====================

/**
 * GET /api/admin/coupons — 优惠券管理列表
 */
async function listAdminCoupons(req, res) {
  try {
    const { status, page, pageSize } = req.query;
    const result = await couponService.listAdminCoupons({
      status: status || undefined,
      page: parseInt(page) || 1,
      pageSize: parseInt(pageSize) || 20
    });
    response.success(res, result);
  } catch (e) {
    response.fail(res, '获取优惠券列表失败', 500);
  }
}

/**
 * POST /api/admin/coupons — 创建优惠券
 */
async function createCoupon(req, res) {
  try {
    const { title, amount, minOrder, validFrom, validTo } = req.body;

    // 必填校验
    if (!title || !amount || !validFrom || !validTo) {
      return response.fail(res, '缺少必填参数：title/amount/validFrom/validTo', 400);
    }

    const result = await couponService.createCoupon({
      title,
      amount,
      minOrder: minOrder ?? 0,
      validFrom,
      validTo
    });
    response.success(res, result, '创建成功');
  } catch (e) {
    if (e.message === 'COUPON_INVALID_DATE') {
      return response.fail(res, '有效期设置错误', 422);
    }
    response.fail(res, '创建优惠券失败', 500);
  }
}

/**
 * POST /api/admin/coupons/:id/grant — 发放优惠券
 */
async function grantCoupon(req, res) {
  try {
    const couponId = parseInt(req.params.id) || 0;
    const { userIds } = req.body;

    if (!couponId) {
      return response.fail(res, '无效的优惠券ID', 400);
    }

    const result = await couponService.grantCoupon(couponId, userIds || null);
    response.success(res, result, '发放成功');
  } catch (e) {
    const errorMap = {
      'COUPON_NOT_FOUND': [404, '优惠券不存在'],
      'USERS_NOT_FOUND': [404, '部分用户不存在']
    };
    const [status, msg] = errorMap[e.message] || [500, '发放失败'];
    response.fail(res, msg, status);
  }
}

module.exports = {
  listAvailableCoupons,
  claimCoupon,
  getMyCoupons,
  listAdminCoupons,
  createCoupon,
  grantCoupon
};

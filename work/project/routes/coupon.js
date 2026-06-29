// @mount /api/coupons (frontend router)
// @mount /api/admin/coupons (admin router)
const express = require('express');
const router = express.Router();
const adminRouter = express.Router();
const { authenticate, hasRole } = require('../middleware/auth');
const ctrl = require('../controllers/couponController');

// ---- Frontend: /api/coupons ----

// GET / → 可领券列表（公开）
router.get('/', ctrl.listAvailableCoupons);

// POST /:id/claim → 领取优惠券
router.post('/:id/claim', authenticate, ctrl.claimCoupon);

// GET /my?orderAmount= → 我的可用券（结算页用）
router.get('/my', authenticate, ctrl.getMyCoupons);

// ---- Admin: /api/admin/coupons ----

// GET / → 优惠券列表（分页+筛选）
adminRouter.get('/', authenticate, hasRole('admin'), ctrl.listAdminCoupons);

// POST / → 创建优惠券
adminRouter.post('/', authenticate, hasRole('admin'), ctrl.createCoupon);

// POST /:id/grant → 发放优惠券
adminRouter.post('/:id/grant', authenticate, hasRole('admin'), ctrl.grantCoupon);

module.exports = { router, adminRouter };

// @mount /api/merchant/refunds

const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole: requireRole } = require('../middleware/permission');
const controller = require('../controllers/merchantRefundController');

// GET /api/merchant/refunds — 商家售后审批列表
router.get('/', authenticate, requireRole(['merchant']), controller.listShopRefunds);

// POST /api/merchant/refunds/:id/approve — 商家审批售后（同意/拒绝）
router.post('/:id/approve', authenticate, requireRole(['merchant']), controller.reviewRefund);

// PUT /api/merchant/refunds/:id/review — 商家审批售后
router.put('/:id/review', authenticate, requireRole(['merchant']), controller.reviewRefund);

module.exports = router;

// @mount /api/admin/refunds
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const adminRefundController = require('../controllers/adminRefundController');

// 所有路由需要管理员认证
router.use(authenticate, hasRole('admin'));

// GET /api/admin/refunds/arbitration — 获取仲裁工单列表
router.get('/arbitration', adminRefundController.getArbitrationList);

// POST /api/admin/refunds/:id/arbitrate — 执行仲裁裁决
router.post('/:id/arbitrate', adminRefundController.arbitrateRefund);

module.exports = router;

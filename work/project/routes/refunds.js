// @mount /api/refunds
const express = require('express');
const router = express.Router();
const { authenticate, requireRole } = require('../middleware/auth');
const refundController = require('../controllers/refundController');

// ── 消费者售后 ──
router.post('/', authenticate, requireRole('user'), refundController.applyRefund);
router.get('/:id', authenticate, refundController.getRefundDetail);

// ── 商家售后审批（供 merchant route 文件引用 controller）──
// 实际路由注册在 routes/merchant-refunds.js，此处仅声明 controller 可用

// ── 平台仲裁（供 admin route 文件引用 controller）──
// 实际路由注册在 routes/admin-refunds.js，此处仅声明 controller 可用

module.exports = router;

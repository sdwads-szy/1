// @mount /api/orders
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const controller = require('../controllers/orderQueryController');

// GET /api/orders — 我的订单列表（分页+状态筛选）
router.get('/', authenticate, hasRole('user'), controller.getOrders);

// GET /api/orders/:id — 订单详情（含子订单+明细+物流）
router.get('/:id', authenticate, hasRole('user'), controller.getOrderDetail);

// POST /api/orders/:id/confirm — 确认收货
router.post('/:id/confirm', authenticate, hasRole('user'), controller.confirmReceive);

module.exports = router;

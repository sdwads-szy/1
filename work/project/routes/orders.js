// @mount /api/orders
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const orderController = require('../controllers/orderController');

// POST /api/orders — 创建订单（下单结算）
router.post('/', authenticate, orderController.createOrder);

// GET /api/orders — 获取用户订单列表
 router.get('/', authenticate, orderController.listOrders);

// GET /api/orders/:id — 获取订单详情
router.get('/:id', authenticate, orderController.getOrderDetail);

// POST /api/orders/:id/confirm — 确认收货
 router.put('/:id/confirm', authenticate, orderController.confirmReceive);

module.exports = router;

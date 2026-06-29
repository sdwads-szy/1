const express = require('express');
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const orderController = require('../controllers/orderController');

// @mount /api/orders
const router = express.Router();

// 用户端接口
router.post('/', authenticate, orderController.createOrder);
router.get('/', authenticate, orderController.getOrderList);
router.get('/:id', authenticate, orderController.getOrderDetail);
router.put('/:id/cancel', authenticate, orderController.cancelOrder);
router.put('/:id/receive', authenticate, orderController.confirmReceipt);

// @mount /api/admin/orders
const adminRouter = express.Router();

// 管理端接口
adminRouter.get('/', authenticate, hasRole('admin'), orderController.adminGetOrderList);
adminRouter.get('/:id', authenticate, hasRole('admin'), orderController.adminGetOrderDetail);
adminRouter.put('/:id/ship', authenticate, hasRole('merchant', 'admin'), orderController.shipOrder);

module.exports = { router, adminRouter };

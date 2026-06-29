// @mount /api/refunds (买家端退款)
// @mount /api/admin/refunds (管理端+商家端退款)

const express = require('express');
const { authenticate, hasRole } = require('../middleware/auth');
const refundController = require('../controllers/refundController');

// 买家端路由 — 挂载于 /api/refunds
const refundRouter = express.Router();
refundRouter.post('/', authenticate, refundController.applyRefund);
refundRouter.get('/', authenticate, refundController.getUserRefunds);
refundRouter.get('/:id', authenticate, refundController.getRefundDetail);

// 管理端 + 商家端路由 — 挂载于 /api/admin/refunds
const adminRefundRouter = express.Router();
adminRefundRouter.get('/', authenticate, hasRole('admin'), refundController.listRefunds);
adminRefundRouter.put('/:id/approve', authenticate, hasRole('merchant'), refundController.approveRefund);
adminRefundRouter.post('/:id/execute', authenticate, hasRole('admin'), refundController.executeRefund);

module.exports = { refundRouter, adminRefundRouter };

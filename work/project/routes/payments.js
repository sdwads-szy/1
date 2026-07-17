// @mount /api/payments
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const paymentController = require('../controllers/paymentController');

// POST /api/payments/pay — 发起支付
router.post('/pay', authenticate, paymentController.initiatePayment);

// GET /api/payments/status/:orderNo — 支付结果轮询
router.get('/status/:orderNo', authenticate, paymentController.getStatus);

module.exports = router;

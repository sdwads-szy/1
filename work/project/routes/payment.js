// @mount /api/payments
const router = require('express').Router();
const paymentController = require('../controllers/paymentController');
const { authenticate } = require('../middleware/auth');

// POST /api/payments/callback — 支付网关回调（无需认证，由网关签名保证安全）
router.post('/callback', paymentController.callback);

// POST /api/payments/:id/pay — 发起支付
router.post('/:id/pay', authenticate, paymentController.pay);

// GET /api/payments/:id/status — 查询支付状态
router.get('/:id/status', authenticate, paymentController.getStatus);

module.exports = router;

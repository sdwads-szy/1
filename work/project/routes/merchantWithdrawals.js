// @mount /api/merchant/withdrawals
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const controller = require('../controllers/merchantWithdrawalController');

// GET  /api/merchant/withdrawals — 商家查自己的提现记录
router.get('/', authenticate, hasRole('merchant'), controller.getWithdrawals);

// POST /api/merchant/withdrawals — 商家提现申请
router.post('/', authenticate, hasRole('merchant'), controller.submitWithdrawal);

module.exports = router;

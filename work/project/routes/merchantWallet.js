const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { requireRole } = require('../middleware/permission');
const controller = require('../controllers/merchantWalletController');

// @mount /api

// 商家钱包余额：查看可提现余额和冻结余额
router.get('/merchant/wallet', authenticate, requireRole(['merchant']), controller.getWalletBalance);

// 商家结算单列表：查看各期结算明细
router.get('/merchant/settlements', authenticate, requireRole(['merchant']), controller.listSettlements);

module.exports = router;

// @mount /api/merchants/register
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const controller = require('../controllers/merchantRegisterController');

// POST /api/merchants/register — 商家入驻申请
router.post('/', authenticate, hasRole('merchant'), controller.applyMerchant);

// GET /api/merchants/register/status — 查询入驻审核状态
router.get('/status', authenticate, hasRole('merchant'), controller.getStatus);

module.exports = router;

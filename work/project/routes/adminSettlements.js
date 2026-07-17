// @mount /api/admin/settlements
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { requireRole } = require('../middleware/permission');
const controller = require('../controllers/adminSettlementController');

// GET / — 平台结算管理：查看所有商家结算单
router.get('/', authenticate, requireRole(['admin']), controller.listSettlements);

// POST /:id/pay — 结算打款：确认打款并标注
router.post('/:id/pay', authenticate, requireRole(['admin']), controller.paySettlement);

module.exports = router;

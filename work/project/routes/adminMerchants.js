// @mount /api/admin/merchants
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole: requireRole } = require('../middleware/permission');
const controller = require('../controllers/adminMerchantController');

// GET  /api/admin/merchants         — 商家列表（支持状态筛选+分页）
// POST /api/admin/merchants/:id/review  — 入驻审核（通过/驳回）
// POST /api/admin/merchants/:id/freeze  — 冻结/解冻商家

router.get('/', authenticate, requireRole('admin'), controller.listMerchants);
router.post('/:id/review', authenticate, requireRole('admin'), controller.reviewMerchant);
router.post('/:id/freeze', authenticate, requireRole('admin'), controller.freezeMerchant);

module.exports = router;

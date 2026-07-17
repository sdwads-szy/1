// @mount /api/admin/withdrawals
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const controller = require('../controllers/adminWithdrawalController');

// GET /api/admin/withdrawals — 平台管理员查看所有提现申请（支持分页+状态筛选）
router.get('/', authenticate, hasRole('admin'), controller.getWithdrawals);

// POST /api/admin/withdrawals/:id/approve — 平台管理员审批提现（通过/驳回）
router.post('/:id/approve', authenticate, hasRole('admin'), controller.approveWithdrawal);

module.exports = router;

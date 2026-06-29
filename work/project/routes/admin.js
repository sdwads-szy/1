// @mount /api/admin
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const adminController = require('../controllers/adminController');

// All admin routes require authentication + admin role
router.use(authenticate, hasRole('admin'));

// ========== 用户管理 ==========
// GET  /api/admin/users        - 用户列表
// PUT  /api/admin/users/:id/ban   - 封禁用户
// PUT  /api/admin/users/:id/unban - 解封用户
// PUT  /api/admin/users/:id/role  - 分配角色
router.get('/users', adminController.listUsers);
router.put('/users/:id/ban', adminController.banUser);
router.put('/users/:id/unban', adminController.unbanUser);
router.put('/users/:id/role', adminController.setUserRole);

// ========== 经营报表 ==========
// GET /api/admin/reports/orders   - 订单报表
// GET /api/admin/reports/payments - 支付报表
// GET /api/admin/reports/refunds  - 退款报表
router.get('/reports/orders', adminController.getOrderReport);
router.get('/reports/payments', adminController.getPaymentReport);
router.get('/reports/refunds', adminController.getRefundReport);

module.exports = router;

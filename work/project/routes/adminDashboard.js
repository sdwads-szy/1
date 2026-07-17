// @mount /api/admin/dashboard
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole: requireRole } = require('../middleware/permission');
const adminDashboardController = require('../controllers/adminDashboardController');

// GET /api/admin/dashboard — 平台数据看板
 router.get('/', authenticate, requireRole(['admin']), adminDashboardController.getAdminDashboard);

module.exports = router;

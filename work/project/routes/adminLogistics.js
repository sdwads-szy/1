// @mount /api/admin/logistics
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole: requireRole } = require('../middleware/permission');
const adminLogisticsController = require('../controllers/adminLogisticsController');

// GET /api/admin/logistics — 物流概览页
router.get('/', authenticate, requireRole(['admin']), adminLogisticsController.getLogisticsOverview);

// GET /api/admin/logistics/monitor — 物流监控数据
router.get('/monitor', authenticate, requireRole(['admin']), adminLogisticsController.getMonitor);

module.exports = router;

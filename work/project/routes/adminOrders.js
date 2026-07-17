// @mount /api/admin/orders
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const adminOrderController = require('../controllers/adminOrderController');

router.get('/', authenticate, hasRole('admin'), adminOrderController.getAdminOrders);

module.exports = router;

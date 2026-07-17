// @mount /api/merchant/dashboard
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const controller = require('../controllers/merchantDashboardController');

router.get('/', authenticate, hasRole('merchant'), controller.getDashboard);

module.exports = router;

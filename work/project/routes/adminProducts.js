// @mount /api/admin/products
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const adminProductController = require('../controllers/adminProductController');

// GET /api/admin/products — 审核列表（按状态筛选，默认草稿）
router.get('/', authenticate, hasRole('admin'), adminProductController.listProducts);

// POST /api/admin/products/:id/review — 商品审核
router.post('/:id/review', authenticate, hasRole('admin'), adminProductController.reviewProduct);

module.exports = router;

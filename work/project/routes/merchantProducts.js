const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const controller = require('../controllers/merchantProductController');

// @mount /api/merchant/products

// GET  /api/merchant/products        — 商品列表（支持状态筛选+分页）
// POST /api/merchant/products        — 发布新商品（SPU+SKU+库存+图片 单TX）
// PUT  /api/merchant/products/:id    — 编辑商品信息

router.get('/', authenticate, hasRole('merchant'), controller.getMerchantProducts);
router.post('/', authenticate, hasRole('merchant'), controller.createMerchantProduct);
router.put('/:id', authenticate, hasRole('merchant'), controller.updateMerchantProduct);

module.exports = router;

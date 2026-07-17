const express = require('express');
const router = express.Router();
// @mount /api — 包含 products / categories / shops 三组路由

const { optionalAuth } = require('../middleware/auth');
const productController = require('../controllers/productController');

// ══ /api/products ══
// GET /api/products — 商品列表：搜索/类目筛选/排序/分页
router.get('/products', optionalAuth, productController.getProducts);

// GET /api/products/:id — 商品详情：SPU+SKU+轮播图+店铺信息
router.get('/products/:id', optionalAuth, productController.getProductDetail);

// ══ /api/categories ══
// GET /api/categories — 全量类目树
router.get('/categories', productController.getCategories);

// ══ /api/shops ══
// GET /api/shops/:id — 店铺信息
router.get('/shops/:id', productController.getShopInfo);

module.exports = router;

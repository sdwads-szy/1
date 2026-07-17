// @mount /api/cart
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const cartController = require('../controllers/cartController');

// GET /api/cart — 获取购物车列表（按店铺分组）
router.get('/', authenticate, hasRole('user'), cartController.getCart);

// POST /api/cart — 添加商品到购物车（UPSERT）
router.post('/', authenticate, hasRole('user'), cartController.addToCart);

// POST /api/cart/select — 选中购物车项准备结算
router.post('/select', authenticate, hasRole('user'), cartController.selectForCheckout);

// PUT /api/cart/:id — 修改购物车商品数量
router.put('/:id', authenticate, hasRole('user'), cartController.updateCartItem);

// DELETE /api/cart/:id — 删除购物车单品
router.delete('/:id', authenticate, hasRole('user'), cartController.removeCartItem);

// PATCH /api/cart/batch-check — 批量勾选/取消勾选
router.patch('/batch-check', authenticate, hasRole('user'), cartController.batchCheck);

// DELETE /api/cart — 清空购物车
router.delete('/', authenticate, hasRole('user'), cartController.clearCart);

module.exports = router;

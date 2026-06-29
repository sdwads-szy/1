// @mount /api/merchant + /api/admin/merchants
const express = require('express');
const { authenticate, hasRole } = require('../middleware/auth');
const ctrl = require('../controllers/merchantController');

const merchantRouter = express.Router();

// ==================== 商家端路由 (/api/merchant) ====================

// 商家注册（无需登录）
merchantRouter.post('/register', ctrl.register);

// 资质提交（需商家角色）
merchantRouter.post('/qualifications', authenticate, hasRole('merchant'), ctrl.submitQualification);

// 店铺信息
merchantRouter.get('/shop', authenticate, hasRole('merchant'), ctrl.getShop);
merchantRouter.put('/shop', authenticate, hasRole('merchant'), ctrl.updateShop);

// 商品管理
merchantRouter.get('/products', authenticate, hasRole('merchant'), ctrl.getProducts);
merchantRouter.post('/products', authenticate, hasRole('merchant'), ctrl.createProduct);
merchantRouter.get('/products/:id', authenticate, hasRole('merchant'), ctrl.getProductById);
merchantRouter.put('/products/:id', authenticate, hasRole('merchant'), ctrl.updateProduct);
merchantRouter.put('/products/:id/list', authenticate, hasRole('merchant'), ctrl.listProduct);
merchantRouter.put('/products/:id/delist', authenticate, hasRole('merchant'), ctrl.delistProduct);

// 订单
merchantRouter.get('/orders', authenticate, hasRole('merchant'), ctrl.getOrders);

// 退款
merchantRouter.get('/refunds', authenticate, hasRole('merchant'), ctrl.getRefunds);

// ==================== 平台后台商家审核路由 (/api/admin/merchants) ====================
const adminMerchantRouter = express.Router();

adminMerchantRouter.get('/', authenticate, hasRole('admin'), ctrl.getAdminMerchants);
adminMerchantRouter.get('/:id', authenticate, hasRole('admin'), ctrl.getAdminMerchantDetail);
adminMerchantRouter.put('/:id/review', authenticate, hasRole('admin'), ctrl.reviewMerchant);
adminMerchantRouter.put('/:id/activate', authenticate, hasRole('admin'), ctrl.activateMerchant);

module.exports = { merchantRouter, adminMerchantRouter };

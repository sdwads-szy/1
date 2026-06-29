// @mount /api

const express = require('express');
const router = express.Router();

const { authenticate, hasRole } = require('../middleware/auth');
const ctrl = require('../controllers/productController');

/* ===== 前台商品接口（公开） ===== */

router.get('/products', ctrl.listProducts);
router.get('/products/:id', ctrl.getProductDetail);

/* ===== 商家商品接口 ===== */

router.get('/merchant/products',
  authenticate,
  hasRole('merchant'),
  ctrl.getMerchantProducts
);

router.get('/merchant/products/:id',
  authenticate,
  hasRole('merchant'),
  ctrl.getMerchantProductDetail
);

router.post('/merchant/products',
  authenticate,
  hasRole('merchant'),
  ctrl.createProduct
);

router.put('/merchant/products/:id',
  authenticate,
  hasRole('merchant'),
  ctrl.updateProduct
);

router.put('/merchant/products/:id/list',
  authenticate,
  hasRole('merchant'),
  ctrl.listProduct
);

router.put('/merchant/products/:id/delist',
  authenticate,
  hasRole('merchant'),
  ctrl.delistProduct
);

/* ===== 管理员商品审核接口 ===== */

router.get('/admin/products',
  authenticate,
  hasRole('admin'),
  ctrl.getAdminProducts
);

router.get('/admin/products/:id',
  authenticate,
  hasRole('admin'),
  ctrl.getAdminProductDetail
);

router.put('/admin/products/:id/review',
  authenticate,
  hasRole('admin'),
  ctrl.reviewProduct
);

module.exports = router;

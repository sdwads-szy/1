// @mount /api/merchant/orders
const router = require('express').Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const controller = require('../controllers/merchantOrderController');

// GET /api/merchant/orders — 商家订单列表（多状态筛选）
router.get('/', authenticate, hasRole('merchant'), controller.getOrderList);

// POST /api/merchant/orders/:id/ship — 发货录单
router.post('/:id/ship', authenticate, hasRole('merchant'), controller.shipOrder);

module.exports = router;

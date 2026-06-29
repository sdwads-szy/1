// @mount /api/cart
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const cartController = require('../controllers/cartController');

router.get('/', authenticate, cartController.getCart);
router.post('/', authenticate, cartController.addToCart);
router.put('/:cartId', authenticate, cartController.updateCartItem);
router.delete('/:cartId', authenticate, cartController.removeCartItem);

module.exports = router;

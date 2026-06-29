// @mount /api/user
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const userController = require('../controllers/userController');

// 个人信息
router.get('/profile', authenticate, userController.getProfile);
router.put('/profile', authenticate, userController.updateProfile);

// 收货地址
router.get('/addresses', authenticate, userController.listAddresses);
router.post('/addresses', authenticate, userController.createAddress);
router.put('/addresses/:id', authenticate, userController.updateAddress);
router.delete('/addresses/:id', authenticate, userController.deleteAddress);

module.exports = router;

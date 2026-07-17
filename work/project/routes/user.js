// @mount /api/user
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const { hasRole } = require('../middleware/permission');
const { getUserProfile: getProfile, updateProfile, getAddresses, createAddress, updateAddress, deleteAddress } = require('../controllers/userController');

// ── 个人信息 ──
// GET /api/user/profile — 获取当前登录用户基本信息
router.get('/profile', authenticate, getProfile);
// PUT /api/user/profile — 修改当前用户昵称/头像
router.put('/profile', authenticate, updateProfile);


// ── 收货地址 ──
// GET /api/user/addresses — 获取当前用户所有收货地址
router.get('/addresses', authenticate, hasRole('user'), getAddresses);
// POST /api/user/addresses — 新增收货地址
router.post('/addresses', authenticate, hasRole('user'), createAddress);
// PUT /api/user/addresses/:id — 修改收货地址
router.put('/addresses/:id', authenticate, hasRole('user'), updateAddress);
// DELETE /api/user/addresses/:id — 删除收货地址
router.delete('/addresses/:id', authenticate, hasRole('user'), deleteAddress);

module.exports = router;

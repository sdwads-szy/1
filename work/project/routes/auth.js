// @mount /api/auth
const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const authController = require('../controllers/authController');

router.post('/login', authController.login);
router.post('/register', authController.register);
router.post('/refresh', authenticate, authController.refresh);

module.exports = router;

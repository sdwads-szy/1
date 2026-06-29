// @mount /api/auth
const router = require('express').Router();
const authController = require('../controllers/authController');
const { authenticate } = require('../middleware/auth');

/** POST /api/auth/login — 手机号+验证码登录 或 微信OAuth登录 */
router.post('/login', authController.login);

/** POST /api/auth/send-code — 发送短信验证码 */
router.post('/send-code', authController.sendCode);

/** POST /api/auth/refresh — 刷新双Token */
router.post('/refresh', authController.refresh);

/** POST /api/auth/logout — 登出（需认证） */
router.post('/logout', authenticate, authController.logout);

module.exports = router;

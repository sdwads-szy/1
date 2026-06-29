const dotenv = require('dotenv');
dotenv.config();

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const path = require('path');

const logger = require('./config/logger');
const { testConnection } = require('./config/db');
const { errorHandler } = require('./middleware/errorHandler');

const app = express();

// --- 安全头 ---
app.use(helmet());

// --- CORS ---
const corsOrigin = process.env.CORS_ORIGIN || '*';
app.use(cors({ origin: corsOrigin, credentials: true }));

// --- 请求日志 ---
const morganFormat = process.env.NODE_ENV === 'production' ? 'combined' : 'dev';
app.use(morgan(morganFormat, { stream: { write: (message) => logger.http(message.trim()) } }));

// --- Body 解析 ---
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: false, limit: '10mb' }));

// --- 静态资源（生产环境前端构建产物） ---
app.use(express.static(path.join(__dirname, 'dist')));

// --- 健康检查 ---
app.get('/api/health', async (_req, res) => {
  try {
    await testConnection();
    res.json({ success: true, message: 'OK', timestamp: new Date().toISOString() });
  } catch (err) {
    res.status(503).json({ success: false, message: 'Database unreachable', timestamp: new Date().toISOString() });
  }
});


const adminRoutes = require('./routes/admin');
const authRoutes = require('./routes/auth');
const cartRoutes = require('./routes/cart');
const categoryRoutes = require('./routes/category');
const couponRoutes = require('./routes/coupon');
const merchantRoutes = require('./routes/merchant');
const orderRoutes = require('./routes/order');
const paymentRoutes = require('./routes/payment');
const productRoutes = require('./routes/product');
const refundRoutes = require('./routes/refund');
const searchRoutes = require('./routes/search');
const userRoutes = require('./routes/user');
app.use('/api/admin', adminRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/cart', cartRoutes);
app.use('/api/categories', categoryRoutes.publicRouter);
app.use('/api/categories', categoryRoutes.adminRouter);
app.use('/api/coupons', couponRoutes.router);
app.use('/api/coupons', couponRoutes.adminRouter);
app.use('/api/merchant', merchantRoutes.merchantRouter);
app.use('/api/merchant', merchantRoutes.adminMerchantRouter);
app.use('/api/orders', orderRoutes.router);
app.use('/api/orders', orderRoutes.adminRouter);
app.use('/api/payments', paymentRoutes);
app.use('/api', productRoutes);
app.use('/api/refunds', refundRoutes.refundRouter);
app.use('/api/refunds', refundRoutes.adminRefundRouter);
app.use('/api/search', searchRoutes);
app.use('/api/user', userRoutes);
// ROUTES_INJECTION_POINT

// --- 404 兜底 ---
app.use((_req, res) => {
  res.status(404).json({ success: false, code: 404, message: '接口不存在', data: null });
});

// --- 全局错误处理（必须在所有路由之后注册） ---
app.use(errorHandler);

// --- 启动服务（非测试环境） ---
if (process.env.NODE_ENV !== 'test') {
  const port = parseInt(process.env.PORT) || 3000;
  app.listen(port, () => {
    logger.info(`Server running on http://localhost:${port}`);
    testConnection()
      .then(() => logger.info('Database connected'))
      .catch((err) => logger.warn('Database connection failed:', err.message));
  });
}

module.exports = app;

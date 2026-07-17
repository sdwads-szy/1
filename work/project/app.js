require('dotenv').config();

const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const morgan = require('morgan');
const path = require('path');
const logger = require('./config/logger');
const { errorHandler } = require('./middleware/errorHandler');

const app = express();

// Trust proxy in production (behind nginx/load balancer)
if (process.env.NODE_ENV === 'production') {
  app.set('trust proxy', 1);
}

// Security headers
app.use(helmet());

// CORS whitelist
const corsOrigin = process.env.CORS_ORIGIN || '*';
app.use(cors({
  origin: corsOrigin,
  credentials: true,
}));

// Body parsing with size limit
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true, limit: '1mb' }));

// Static files
app.use(express.static(path.join(__dirname, 'public')));

// HTTP request logging via morgan → winston
const morganStream = {
  write: (message) => logger.info(message.trim()),
};
app.use(morgan('combined', { stream: morganStream }));

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ success: true, message: 'OK', timestamp: new Date().toISOString() });
});


const adminDashboardRoutes = require('./routes/adminDashboard');
const adminLogisticsRoutes = require('./routes/adminLogistics');
const adminMerchantsRoutes = require('./routes/adminMerchants');
const adminOrdersRoutes = require('./routes/adminOrders');
const adminProductsRoutes = require('./routes/adminProducts');
const adminSettlementsRoutes = require('./routes/adminSettlements');
const adminWithdrawalsRoutes = require('./routes/adminWithdrawals');
const authRoutes = require('./routes/auth');
const cartRoutes = require('./routes/cart');
const merchantDashboardRoutes = require('./routes/merchantDashboard');
const merchantProductsRoutes = require('./routes/merchantProducts');
const merchantRegisterRoutes = require('./routes/merchantRegister');
const merchantWalletRoutes = require('./routes/merchantWallet');
const merchantWithdrawalsRoutes = require('./routes/merchantWithdrawals');
const orderQueryRoutes = require('./routes/orderQuery');
const productsRoutes = require('./routes/products');
const userRoutes = require('./routes/user');
const adminRefundsRoutes = require('./routes/adminRefunds');
const merchantOrdersRoutes = require('./routes/merchantOrders');
const merchantRefundsRoutes = require('./routes/merchantRefunds');
const ordersRoutes = require('./routes/orders');
const paymentsRoutes = require('./routes/payments');
const refundsRoutes = require('./routes/refunds');

app.use('/api/admin/dashboard', adminDashboardRoutes);
app.use('/api/admin/logistics', adminLogisticsRoutes);
app.use('/api/admin/merchants', adminMerchantsRoutes);
app.use('/api/admin/orders', adminOrdersRoutes);
app.use('/api/admin/products', adminProductsRoutes);
app.use('/api/admin/settlements', adminSettlementsRoutes);
app.use('/api/admin/withdrawals', adminWithdrawalsRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/cart', cartRoutes);
app.use('/api/merchant/dashboard', merchantDashboardRoutes);
app.use('/api/merchant/products', merchantProductsRoutes);
app.use('/api/merchants/register', merchantRegisterRoutes);
app.use('/api', merchantWalletRoutes);
app.use('/api/merchant/withdrawals', merchantWithdrawalsRoutes);
app.use('/api/orders', orderQueryRoutes);
app.use('/api', productsRoutes);
app.use('/api/user', userRoutes);
app.use('/api/admin/refunds', adminRefundsRoutes);
app.use('/api/merchant/orders', merchantOrdersRoutes);
app.use('/api/merchant/refunds', merchantRefundsRoutes);
app.use('/api/orders', ordersRoutes);
app.use('/api/payments', paymentsRoutes);
app.use('/api/refunds', refundsRoutes);

// ROUTES_INJECTION_POINT

// 404 handler for unmatched routes
app.use((req, res) => {
  res.status(404).json({ success: false, code: 404, message: '接口不存在' });
});

// Global error handler (must be the last middleware)
app.use(errorHandler);

const PORT = process.env.PORT || 3000;

if (require.main === module) {
  app.listen(PORT, () => {
    logger.info(`Server running on port ${PORT} in ${process.env.NODE_ENV || 'development'} mode`);
  });
}

module.exports = app;

import { createRouter, createWebHistory } from 'vue-router';
// IMPORT_INJECTION_POINT

const routes = [
  // ==================== 前台买家端 ====================
  { path: '/', name: 'Home', component: () => import('@/pages/frontend/home/Home.vue') },
  { path: '/login', name: 'Login', component: () => import('@/pages/frontend/auth/Login.vue') },
  { path: '/register', name: 'Register', component: () => import('@/pages/frontend/auth/Register.vue') },
  { path: '/products', name: 'ProductList', component: () => import('@/pages/frontend/product/ProductList.vue') },
  { path: '/products/:productId', name: 'ProductDetail', component: () => import('@/pages/frontend/product/ProductDetail.vue') },
  { path: '/category/:id', name: 'CategoryProducts', component: () => import('@/pages/frontend/product/ProductList.vue') },
  { path: '/search', name: 'SearchResult', component: () => import('@/pages/frontend/search/SearchResult.vue') },
  { path: '/cart', name: 'Cart', component: () => import('@/pages/frontend/cart/Cart.vue'), meta: { requiresAuth: true } },
  { path: '/checkout', name: 'Checkout', component: () => import('@/pages/frontend/checkout/Checkout.vue'), meta: { requiresAuth: true } },
  { path: '/orders', name: 'OrderList', component: () => import('@/pages/frontend/order/OrderList.vue'), meta: { requiresAuth: true } },
  { path: '/orders/:orderId', name: 'OrderDetail', component: () => import('@/pages/frontend/order/OrderDetail.vue'), meta: { requiresAuth: true } },
  { path: '/payment/:orderId', name: 'Payment', component: () => import('@/pages/frontend/payment/Payment.vue'), meta: { requiresAuth: true } },
  { path: '/payment/:orderId/result', name: 'PaymentResult', component: () => import('@/pages/frontend/payment/PaymentResult.vue'), meta: { requiresAuth: true } },
  { path: '/refund/apply/:orderId', name: 'RefundApply', component: () => import('@/pages/frontend/refund/RefundApply.vue'), meta: { requiresAuth: true } },
  { path: '/refund/status', name: 'RefundStatus', component: () => import('@/pages/frontend/refund/RefundStatus.vue'), meta: { requiresAuth: true } },
  { path: '/coupons', name: 'CouponCenter', component: () => import('@/pages/frontend/coupon/CouponCenter.vue'), meta: { requiresAuth: true } },
  { path: '/profile', name: 'Profile', component: () => import('@/pages/frontend/user/Profile.vue'), meta: { requiresAuth: true } },
  { path: '/addresses', name: 'AddressList', component: () => import('@/pages/frontend/user/AddressList.vue'), meta: { requiresAuth: true } },
  { path: '/addresses/:id', name: 'AddressEdit', component: () => import('@/pages/frontend/user/AddressEdit.vue'), meta: { requiresAuth: true } },

  // ==================== 商家端 ====================
  { path: '/merchant/register', name: 'MerchantRegister', component: () => import('@/pages/merchant/onboarding/Register.vue') },
  { path: '/merchant/qualification', name: 'MerchantQualification', component: () => import('@/pages/merchant/onboarding/Qualification.vue'), meta: { requiresAuth: true } },
  { path: '/merchant/shop-edit', name: 'MerchantShopEdit', component: () => import('@/pages/merchant/onboarding/ShopEdit.vue'), meta: { requiresAuth: true } },
  { path: '/merchant/progress', name: 'MerchantProgress', component: () => import('@/pages/merchant/onboarding/Progress.vue'), meta: { requiresAuth: true } },
  { path: '/merchant/products', name: 'MerchantProductList', component: () => import('@/pages/merchant/product/ProductList.vue'), meta: { requiresAuth: true } },
  { path: '/merchant/product/publish', name: 'MerchantProductPublish', component: () => import('@/pages/merchant/product/ProductPublish.vue'), meta: { requiresAuth: true } },
  { path: '/merchant/product/publish/:id', name: 'MerchantProductEdit', component: () => import('@/pages/merchant/product/ProductPublish.vue'), meta: { requiresAuth: true } },
  { path: '/merchant/orders', name: 'MerchantOrderList', component: () => import('@/pages/merchant/order/OrderList.vue'), meta: { requiresAuth: true } },
  { path: '/merchant/refunds', name: 'MerchantRefundList', component: () => import('@/pages/merchant/refund/RefundList.vue'), meta: { requiresAuth: true } },

  // ==================== 平台后台 ====================
  { path: '/admin/users', name: 'AdminUserList', component: () => import('@/pages/admin/user/UserList.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/users/:id', name: 'AdminUserDetail', component: () => import('@/pages/admin/user/UserDetail.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/categories', name: 'AdminCategoryTree', component: () => import('@/pages/admin/category/CategoryTree.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/merchants', name: 'AdminMerchantList', component: () => import('@/pages/admin/merchant/MerchantList.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/merchants/:id', name: 'AdminMerchantDetail', component: () => import('@/pages/admin/merchant/MerchantDetail.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/products', name: 'AdminProductAudit', component: () => import('@/pages/admin/product/ProductAudit.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/products/:id', name: 'AdminProductDetail', component: () => import('@/pages/admin/product/ProductDetail.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/orders', name: 'AdminOrderList', component: () => import('@/pages/admin/order/OrderList.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/orders/:id', name: 'AdminOrderDetail', component: () => import('@/pages/admin/order/OrderDetail.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/coupons', name: 'AdminCouponList', component: () => import('@/pages/admin/coupon/CouponList.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/coupons/create', name: 'AdminCouponCreate', component: () => import('@/pages/admin/coupon/CouponCreate.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/refunds', name: 'AdminRefundList', component: () => import('@/pages/admin/refund/RefundList.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/refunds/:id', name: 'AdminRefundDetail', component: () => import('@/pages/admin/refund/RefundDetail.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/reports/dashboard', name: 'AdminDashboard', component: () => import('@/pages/admin/reports/Dashboard.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  // ROUTES_INJECTION_POINT

  // ==================== 404 通配 ====================
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/pages/frontend/home/Home.vue') },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token');

  if (to.meta.requiresAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } });
  } else if (to.meta.requiresAdmin && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } });
  } else {
    next();
  }
});

export default router;

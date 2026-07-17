import { createRouter, createWebHistory } from 'vue-router';

/**
 * 路由配置 — 星链商城
 *
 * meta 字段说明:
 *   title        — 页面标题
 *   requiresAuth — 是否需要登录
 *   role         — 需要的角色: 'user' | 'merchant' | 'admin'
 *   guest        — 仅未登录可访问
 */

const routes = [
  // ═══════════════════════════════════════════
  // 消费者端 — 公开浏览（无需登录）
  // ═══════════════════════════════════════════
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/home/index.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/pages/search/index.vue'),
    meta: { title: '搜索' },
  },
  {
    path: '/category/:id',
    name: 'Category',
    component: () => import('@/pages/category/list.vue'),
    meta: { title: '分类浏览' },
  },
  {
    path: '/product/:id',
    name: 'ProductDetail',
    component: () => import('@/pages/product/detail.vue'),
    meta: { title: '商品详情' },
  },

  // ═══════════════════════════════════════════
  // 消费者端 — 需要登录 (role=user)
  // ═══════════════════════════════════════════
  {
    path: '/cart',
    name: 'Cart',
    component: () => import('@/pages/cart/index.vue'),
    meta: { title: '购物车', requiresAuth: true, role: 'user' },
  },
  {
    path: '/checkout',
    name: 'Checkout',
    component: () => import('@/pages/checkout/index.vue'),
    meta: { title: '下单结算', requiresAuth: true, role: 'user' },
  },
  {
    path: '/checkout/pay',
    name: 'CheckoutPay',
    component: () => import('@/pages/checkout/pay.vue'),
    meta: { title: '支付', requiresAuth: true, role: 'user' },
  },
  {
    path: '/orders',
    name: 'OrderList',
    component: () => import('@/pages/orders/list.vue'),
    meta: { title: '我的订单', requiresAuth: true, role: 'user' },
  },
  {
    path: '/orders/:id',
    name: 'OrderDetail',
    component: () => import('@/pages/orders/detail.vue'),
    meta: { title: '订单详情', requiresAuth: true, role: 'user' },
  },
  {
    path: '/orders/:id/refund',
    name: 'RefundApply',
    component: () => import('@/pages/orders/refund/apply.vue'),
    meta: { title: '申请售后', requiresAuth: true, role: 'user' },
  },
  {
    path: '/orders/:id/refund/detail',
    name: 'RefundDetail',
    component: () => import('@/pages/orders/refund/detail.vue'),
    meta: { title: '售后详情', requiresAuth: true, role: 'user' },
  },
  {
    path: '/user/profile',
    name: 'UserProfile',
    component: () => import('@/pages/user/profile.vue'),
    meta: { title: '个人信息', requiresAuth: true, role: 'user' },
  },

  // ═══════════════════════════════════════════
  // 认证页面（仅未登录可访问）
  // ═══════════════════════════════════════════
  {
    path: '/auth/login',
    name: 'Login',
    component: () => import('@/pages/auth/login.vue'),
    meta: { title: '登录', guest: true },
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('@/pages/admin/login.vue'),
    meta: { title: '后台登录', guest: true },
  },

  // ═══════════════════════════════════════════
  // 商家后台 — 需要登录 (role=merchant)
  // ═══════════════════════════════════════════
  {
    path: '/merchant/register',
    name: 'MerchantRegister',
    component: () => import('@/pages/merchant/register/index.vue'),
    meta: { title: '商家入驻', requiresAuth: true, role: 'merchant' },
  },
  {
    path: '/merchant/register/status',
    name: 'MerchantRegisterStatus',
    component: () => import('@/pages/merchant/register/status.vue'),
    meta: { title: '审核进度', requiresAuth: true, role: 'merchant' },
  },
  {
    path: '/merchant/dashboard',
    name: 'MerchantDashboard',
    component: () => import('@/pages/merchant/dashboard/index.vue'),
    meta: { title: '经营数据', requiresAuth: true, role: 'merchant' },
  },
  {
    path: '/merchant/products',
    name: 'MerchantProducts',
    component: () => import('@/pages/merchant/products/list.vue'),
    meta: { title: '商品管理', requiresAuth: true, role: 'merchant' },
  },
  {
    path: '/merchant/orders',
    name: 'MerchantOrders',
    component: () => import('@/pages/merchant/orders/list.vue'),
    meta: { title: '订单管理', requiresAuth: true, role: 'merchant' },
  },
  {
    path: '/merchant/orders/:id/shipping',
    name: 'MerchantShipping',
    component: () => import('@/pages/merchant/orders/shipping.vue'),
    meta: { title: '发货处理', requiresAuth: true, role: 'merchant' },
  },
  {
    path: '/merchant/refunds',
    name: 'MerchantRefunds',
    component: () => import('@/pages/merchant/refunds/list.vue'),
    meta: { title: '售后管理', requiresAuth: true, role: 'merchant' },
  },
  {
    path: '/merchant/wallet',
    name: 'MerchantWallet',
    component: () => import('@/pages/merchant/wallet/index.vue'),
    meta: { title: '钱包结算', requiresAuth: true, role: 'merchant' },
  },

  // ═══════════════════════════════════════════
  // 平台后台 — 需要登录 (role=admin)
  // ═══════════════════════════════════════════
  {
    path: '/admin/dashboard',
    name: 'AdminDashboard',
    component: () => import('@/pages/admin/dashboard/index.vue'),
    meta: { title: '数据看板', requiresAuth: true, role: 'admin' },
  },
  {
    path: '/admin/merchants/review',
    name: 'AdminMerchantReview',
    component: () => import('@/pages/admin/merchants/review.vue'),
    meta: { title: '商家审核', requiresAuth: true, role: 'admin' },
  },
  {
    path: '/admin/merchants',
    name: 'AdminMerchants',
    component: () => import('@/pages/admin/merchants/index.vue'),
    meta: { title: '商家管理', requiresAuth: true, role: 'admin' },
  },
  {
    path: '/admin/products/review',
    name: 'AdminProductReview',
    component: () => import('@/pages/admin/products/review.vue'),
    meta: { title: '商品审核', requiresAuth: true, role: 'admin' },
  },
  {
    path: '/admin/orders',
    name: 'AdminOrders',
    component: () => import('@/pages/admin/orders/list.vue'),
    meta: { title: '全局订单', requiresAuth: true, role: 'admin' },
  },
  {
    path: '/admin/refunds/arbitration',
    name: 'AdminRefundArbitration',
    component: () => import('@/pages/admin/refunds/arbitration.vue'),
    meta: { title: '退款仲裁', requiresAuth: true, role: 'admin' },
  },
  {
    path: '/admin/finance/settlements',
    name: 'AdminSettlements',
    component: () => import('@/pages/admin/finance/settlements.vue'),
    meta: { title: '结算管理', requiresAuth: true, role: 'admin' },
  },
  {
    path: '/admin/logistics',
    name: 'AdminLogistics',
    component: () => import('@/pages/admin/logistics/index.vue'),
    meta: { title: '物流监控', requiresAuth: true, role: 'admin' },
  },

  // ═══════════════════════════════════════════
  // 404 兜底
  // ═══════════════════════════════════════════
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/pages/404.vue'),
    meta: { title: '页面不存在' },
  },
  {
    path: '/admin/merchants-review',
    name: 'AdminMerchantsReview',
    redirect: { name: 'AdminMerchantReview' },
  },
  {
    path: '/orders-list',
    name: 'OrdersList',
    redirect: { name: 'OrderList' },
  },
  {
    path: '/auth-login',
    name: 'AuthLogin',
    redirect: { name: 'Login' },
  },

];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  },
});

/**
 * 全局前置守卫
 *
 * 规则:
 *   1. meta.guest=true   → 已登录则重定向到对应首页
 *   2. meta.requiresAuth → 未登录则重定向到登录页 (带 redirect 参数)
 *   3. meta.role          → 角色不匹配则重定向到对应首页
 *   4. token 过期         → 清除 token 并重定向登录页
 */
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 星链商城` : '星链商城';

  const token = localStorage.getItem('auth_token');
  const requiresAuth = to.meta.requiresAuth;
  const requiredRole = to.meta.role;
  const isGuestOnly = to.meta.guest;

  // ── 仅未登录可访问 ──
  if (isGuestOnly) {
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.role === 'merchant' || payload.role === 'admin') {
          return next(payload.role === 'admin' ? '/admin/dashboard' : '/merchant/dashboard');
        }
        return next('/');
      } catch {
        // token 损坏，允许继续
      }
    }
    return next();
  }

  // ── 公开路由 → 直接放行 ──
  if (!requiresAuth) {
    return next();
  }

  // ── 需要登录但无 token ──
  if (!token) {
    const loginPath = requiredRole === 'admin' || requiredRole === 'merchant'
      ? '/admin/login'
      : '/auth/login';
    return next({ path: loginPath, query: { redirect: to.fullPath } });
  }

  // ── 校验 token ──
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const isExpired = payload.exp * 1000 < Date.now();

    if (isExpired) {
      localStorage.removeItem('auth_token');
      const loginPath = requiredRole === 'admin' || requiredRole === 'merchant'
        ? '/admin/login'
        : '/auth/login';
      return next({ path: loginPath, query: { redirect: to.fullPath } });
    }

    if (requiredRole && payload.role !== requiredRole) {
      if (payload.role === 'admin') return next('/admin/dashboard');
      if (payload.role === 'merchant') return next('/merchant/dashboard');
      return next('/');
    }

    return next();
  } catch {
    localStorage.removeItem('auth_token');
    const loginPath = requiredRole === 'admin' || requiredRole === 'merchant'
      ? '/admin/login'
      : '/auth/login';
    return next({ path: loginPath, query: { redirect: to.fullPath } });
  }
});

export default router;

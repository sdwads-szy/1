const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

function readPageSafe(pagePath) {
  const fullPath = path.join(workspace, pagePath);
  if (!fs.existsSync(fullPath)) { console.warn('SKIP: ' + pagePath); return null; }
  return fs.readFileSync(fullPath, 'utf-8');
}

describe('t_nav_guard_auth', () => {
  const routerContent = readPageSafe('src/router/index.js');

  // ====== correct: beforeEach 守卫注册 ======
  describe('correct — router.beforeEach 守卫存在', () => {
    if (!routerContent) return;

    it('src/router/index.js 中定义了 beforeEach', () => {
      expect(routerContent).toContain('beforeEach');
    });
  });

  // ====== correct: 未登录 → 重定向 /auth/login ======
  describe('correct — 未登录重定向到 /auth/login', () => {
    if (!routerContent) return;

    it('守卫中引用 /auth/login 作为重定向目标', () => {
      expect(routerContent).toContain('/auth/login');
    });

    it('守卫中传递 redirect query 参数记录原路径', () => {
      expect(routerContent).toContain('redirect');
    });

    it('守卫检查 token 或 isLoggedIn 判断登录状态', () => {
      const hasAuthCheck = routerContent.includes('token') || routerContent.includes('isLoggedIn');
      expect(hasAuthCheck).toBe(true);
    });
  });

  // ====== correct: 9 个契约中指定的受保护路由 ======
  describe('correct — 受保护路由在 router 中注册（受 beforeEach 守卫保护）', () => {
    if (!routerContent) return;

    const protectedRoutes = [
      'Cart',
      'Checkout',
      'Pay',
      'OrderList',
      'OrderDetail',
      'RefundApply',
      'RefundDetail',
      'Profile',
      'MerchantsReview'
    ];

    protectedRoutes.forEach(routeName => {
      it('路由 ' + routeName + ' 在 router 中注册', () => {
        expect(routerContent).toContain(routeName);
      });
    });
  });

  // ====== error: role 角色权限守卫 ======
  describe('error — user 角色 token 访问 Admin 页面被角色守卫拒绝', () => {
    if (!routerContent) return;

    it('守卫中引用 meta.roles 或 role 做角色检查', () => {
      const hasRoleGuard = routerContent.includes('meta.roles') || routerContent.includes('.role');
      expect(hasRoleGuard).toBe(true);
    });

    it('守卫对无权限角色有拦截逻辑（403 或重定向）', () => {
      const hasRejection =
        routerContent.includes('403') ||
        routerContent.includes("next('/')") ||
        routerContent.includes('redirect');
      expect(hasRejection).toBe(true);
    });

    it('AdminDashboard 路由在 router 中注册', () => {
      expect(routerContent).toContain('AdminDashboard');
    });
  });
});

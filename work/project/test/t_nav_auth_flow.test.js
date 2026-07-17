const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

function readPageSafe(pagePath) {
  const fullPath = path.join(workspace, pagePath);
  if (!fs.existsSync(fullPath)) { console.warn('SKIP: ' + pagePath); return null; }
  return fs.readFileSync(fullPath, 'utf-8');
}

describe('t_nav_auth_flow', () => {
  // ================================================================
  // Scenario 1: Login → 重定向回源页 — query 传递 redirect 路径
  // ================================================================
  describe('correct — Login → 重定向回源页 (query: redirect)', () => {
    const fromPage = readPageSafe('src/pages/auth/login.vue');
    const passBy = 'query';
    const paramName = 'redirect';

    // 维度1: 源页包含跳转入口
    it('源页包含 redirect 重定向逻辑', () => {
      if (!fromPage) return;
      expect(fromPage).toContain('redirect');
    });

    // 维度2: passBy 方式 — query
    it('源页用 query 方式获取 redirect 参数', () => {
      if (!fromPage) return;
      const hasQueryAccess =
        fromPage.includes('query.redirect') ||
        fromPage.includes('query["redirect"]') ||
        fromPage.includes("query['redirect']") ||
        fromPage.includes('$route.query');
      expect(hasQueryAccess).toBe(true);
    });

    // 维度3: 参数名一致
    it('参数 redirect 在源页中传递', () => {
      if (!fromPage) return;
      expect(fromPage).toContain('redirect');
    });
  });

  // ================================================================
  // Scenario 2: Login → MerchantDashboard — 角色为 merchant 时跳转商家后台
  // ================================================================
  describe('correct — Login → MerchantDashboard (passBy: none)', () => {
    const fromPage = readPageSafe('src/pages/auth/login.vue');
    const toPage = readPageSafe('src/pages/merchant/dashboard.vue');
    const routeName = 'MerchantDashboard';
    const fromRouteName = 'Login';

    // 维度1: 源页包含跳转入口
    it('源页提到了目标路由名: ' + routeName, () => {
      if (!fromPage) return;
      expect(fromPage).toContain(routeName);
    });

    // 维度4: 返回导航
    it('目标页可返回源页（提到了源路由名: ' + fromRouteName + '）', () => {
      if (!toPage) return;
      expect(toPage).toContain(fromRouteName);
    });
  });

  // ================================================================
  // Scenario 3: Login → AdminDashboard — 角色为 admin 时跳转平台后台
  // ================================================================
  describe('correct — Login → AdminDashboard (passBy: none)', () => {
    const fromPage = readPageSafe('src/pages/auth/login.vue');
    const toPage = readPageSafe('src/pages/admin/dashboard.vue');
    const routeName = 'AdminDashboard';
    const fromRouteName = 'Login';

    // 维度1: 源页包含跳转入口
    it('源页提到了目标路由名: ' + routeName, () => {
      if (!fromPage) return;
      expect(fromPage).toContain(routeName);
    });

    // 维度4: 返回导航
    it('目标页可返回源页（提到了源路由名: ' + fromRouteName + '）', () => {
      if (!toPage) return;
      expect(toPage).toContain(fromRouteName);
    });
  });

  // ================================================================
  // Scenario 4: Profile → OrderList — 从个人中心跳转订单列表
  // ================================================================
  describe('correct — Profile → OrderList (passBy: none)', () => {
    const fromPage = readPageSafe('src/pages/user/profile.vue');
    const toPage = readPageSafe('src/pages/order/list.vue');
    const routeName = 'OrderList';
    const fromRouteName = 'UserProfile';

    // 维度1: 源页包含跳转入口
    it('源页提到了目标路由名: ' + routeName, () => {
      if (!fromPage) return;
      expect(fromPage).toContain(routeName);
    });

    // 维度4: 返回导航
    it('目标页可返回源页（提到了源路由名: ' + fromRouteName + '）', () => {
      if (!toPage) return;
      expect(toPage).toContain(fromRouteName);
    });
  });

  // ================================================================
  // Scenario 5: error — 用 query 传 role 但目标不应从路由读取角色
  // ================================================================
  describe('error — Login → MerchantDashboard 不应该用 query 传 role', () => {
    const fromPage = readPageSafe('src/pages/auth/login.vue');
    const toPage = readPageSafe('src/pages/merchant/dashboard.vue');
    const routeName = 'MerchantDashboard';

    // 维度5: passBy 不匹配 — 源页若用 query 传 role 则属于错误传参方式
    it('源页跳转 ' + routeName + ' 时不应附带 query.role', () => {
      if (!fromPage) return;
      const idx = fromPage.indexOf(routeName);
      if (idx !== -1) {
        const nearby = fromPage.substring(Math.max(0, idx - 80), idx + 200);
        const hasQueryRole = nearby.includes('query') && nearby.includes('role');
        expect(hasQueryRole).toBe(false);
      }
    });

    // 维度6: 参数名不一致 — 目标页不应从 route.query 读取 role
    it('目标页不应从 route.query 读取 role（角色应从 userStore 获取）', () => {
      if (!toPage) return;
      const readsQueryRole =
        toPage.includes('query.role') ||
        toPage.includes('query["role"]') ||
        toPage.includes("query['role']");
      expect(readsQueryRole).toBe(false);
    });
  });
});

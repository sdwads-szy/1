const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

function readPageSafe(pagePath) {
  const fullPath = path.join(workspace, pagePath);
  if (!fs.existsSync(fullPath)) { console.warn('SKIP: ' + pagePath); return null; }
  return fs.readFileSync(fullPath, 'utf-8');
}

describe('t_nav_merchant_onboarding', () => {
  // ================================================================
  // Nav 1: MerchantRegister → MerchantRegisterStatus（提交申请→审核状态页）
  // 真理: router.MerchantRegisterStatus = '/merchant/register/status'，无动态段
  // ================================================================
  describe('nav_merchant_register_status', () => {
    const fromPagePath = 'src/pages/merchant/register/index.vue';
    const toPagePath   = 'src/pages/merchant/register/status.vue';
    const routeName    = 'MerchantRegisterStatus';
    const passBy       = 'none';
    const params       = [];

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    // ==== 维度1: 源页包含跳转入口 ====
    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;

      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    // ==== 维度2: passBy 方式（none → 跳过）====

    // ==== 维度3: 参数名一致（无参数 → 跳过）====

    // ==== 维度4: 返回导航 ====
    describe('correct — 返回导航', () => {
      if (!toPage) return;

      it('目标页可返回源页（提到了源路由名 MerchantRegister）', () => {
        expect(toPage).toContain('MerchantRegister');
      });
    });

    // ==== 维度5: error — passBy 不匹配 ====
    describe('error — passBy 不匹配', () => {
      if (!fromPage) return;

      it('源页不应使用 query 传参（passBy=none，目标无动态段）', () => {
        const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
        if (hasQuery) {
          fail('passBy 冲突: 预期 none 但源页用了 query');
        }
      });

      it('源页不应使用 params 传参（passBy=none，目标无动态段）', () => {
        const hasParams = fromPage.includes('params:') || fromPage.includes('params :');
        if (hasParams) {
          fail('passBy 冲突: 预期 none 但源页用了 params');
        }
      });
    });

    // ==== 维度6: error — 参数名不一致 ====
    describe('error — 参数名不一致', () => {
      if (!fromPage || !toPage) return;

      it('目标页不应依赖 query.applicationId（状态应从 merchantStore 获取）', () => {
        expect(toPage.includes('applicationId')).toBe(false);
      });

      it('源页不应传递 applicationId（状态应从 merchantStore 获取）', () => {
        expect(fromPage.includes('applicationId')).toBe(false);
      });
    });
  });

  // ================================================================
  // Nav 2: MerchantRegisterStatus → MerchantDashboard（审核通过→商家后台）
  // 场景指定: router.push({name:'MerchantDashboard'}), passBy=none
  // ================================================================
  describe('nav_merchant_status_dashboard', () => {
    const fromPagePath = 'src/pages/merchant/register/status.vue';
    const toPagePath   = 'src/pages/merchant/dashboard/index.vue';
    const routeName    = 'MerchantDashboard';
    const passBy       = 'none';
    const params       = [];

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    // ==== 维度1: 源页包含跳转入口 ====
    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;

      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    // ==== 维度2: passBy 方式（none → 跳过）====

    // ==== 维度3: 参数名一致（无参数 → 跳过）====



    // ==== 维度5: error — passBy 不匹配 ====
    describe('error — passBy 不匹配', () => {
      if (!fromPage) return;

      it('源页不应使用 query 传参（passBy=none，目标无动态段）', () => {
        const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
        if (hasQuery) {
          fail('passBy 冲突: 预期 none 但源页用了 query');
        }
      });

      it('源页不应使用 params 传参（passBy=none，目标无动态段）', () => {
        const hasParams = fromPage.includes('params:') || fromPage.includes('params :');
        if (hasParams) {
          fail('passBy 冲突: 预期 none 但源页用了 params');
        }
      });
    });
  });
});

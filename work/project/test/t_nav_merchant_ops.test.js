const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

function readPageSafe(pagePath) {
  const fullPath = path.join(workspace, pagePath);
  if (!fs.existsSync(fullPath)) { console.warn('SKIP: ' + pagePath); return null; }
  return fs.readFileSync(fullPath, 'utf-8');
}

describe('t_nav_merchant_ops', () => {
  // ================================================================
  // Nav 1: MerchantDashboard → MerchantProducts (passBy=none)
  // ================================================================
  describe('MerchantDashboard → MerchantProducts', () => {
    const fromPagePath = 'src/pages/merchant/dashboard/index.vue';
    const toPagePath   = 'src/pages/merchant/products/list.vue';
    const routeName    = 'MerchantProducts';
    const passBy       = 'none';
    const params       = [];

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;
      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    describe('correct — 返回导航', () => {
      if (!toPage) return;
      it('目标页可返回源页（提到了源路由名）', () => {
        expect(toPage).toContain('MerchantDashboard');
      });
    });
  });

  // ================================================================
  // Nav 2: MerchantDashboard → MerchantOrders (passBy=none)
  // ================================================================
  describe('MerchantDashboard → MerchantOrders', () => {
    const fromPagePath = 'src/pages/merchant/dashboard/index.vue';
    const toPagePath   = 'src/pages/merchant/orders/list.vue';
    const routeName    = 'MerchantOrders';
    const passBy       = 'none';
    const params       = [];

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;
      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    describe('correct — 返回导航', () => {
      if (!toPage) return;
      it('目标页可返回源页（提到了源路由名）', () => {
        expect(toPage).toContain('MerchantDashboard');
      });
    });
  });

  // ================================================================
  // Nav 3: MerchantDashboard → MerchantRefunds (passBy=none)
  // ================================================================
  describe('MerchantDashboard → MerchantRefunds', () => {
    const fromPagePath = 'src/pages/merchant/dashboard/index.vue';
    const toPagePath   = 'src/pages/merchant/refunds/list.vue';
    const routeName    = 'MerchantRefunds';
    const passBy       = 'none';
    const params       = [];

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;
      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    describe('correct — 返回导航', () => {
      if (!toPage) return;
      it('目标页可返回源页（提到了源路由名）', () => {
        expect(toPage).toContain('MerchantDashboard');
      });
    });
  });

  // ================================================================
  // Nav 4: MerchantDashboard → MerchantWallet (passBy=none)
  // ================================================================
  describe('MerchantDashboard → MerchantWallet', () => {
    const fromPagePath = 'src/pages/merchant/dashboard/index.vue';
    const toPagePath   = 'src/pages/merchant/wallet/index.vue';
    const routeName    = 'MerchantWallet';
    const passBy       = 'none';
    const params       = [];

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;
      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    describe('correct — 返回导航', () => {
      if (!toPage) return;
      it('目标页可返回源页（提到了源路由名）', () => {
        expect(toPage).toContain('MerchantDashboard');
      });
    });
  });

  // ================================================================
  // Nav 5: MerchantOrders → MerchantShipping (passBy=params, param=id)
  // ================================================================
  describe('MerchantOrders → MerchantShipping', () => {
    const fromPagePath = 'src/pages/merchant/orders/list.vue';
    const toPagePath   = 'src/pages/merchant/orders/shipping.vue';
    const routeName    = 'MerchantShipping';
    const passBy       = 'params';
    const params       = ['id'];

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;
      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    describe('correct — passBy 方式: ' + passBy, () => {
      if (!fromPage) return;
      it('源页用 params 传参', () => {
        expect(fromPage.includes('params:') || fromPage.includes('params :')).toBe(true);
      });
    });

    describe('correct — 参数名一致', () => {
      if (!fromPage) return;
      it('参数 id 在源页中传递', () => {
        expect(fromPage).toContain('id');
      });
    });

    describe('correct — 返回导航', () => {
      if (!toPage) return;
      it('目标页可返回源页（提到了源路由名）', () => {
        expect(toPage).toContain('MerchantOrders');
      });
    });
  });

  // ================================================================
  // Nav 6: MerchantRefunds → RefundDetail (passBy=params, param=requestNo)
  // ================================================================
  describe('MerchantRefunds → RefundDetail', () => {
    const fromPagePath = 'src/pages/merchant/refunds/list.vue';
    const toPagePath   = 'src/pages/merchant/refunds/detail.vue';
    const routeName    = 'RefundDetail';
    const passBy       = 'params';
    const params       = ['requestNo'];

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;
      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    describe('correct — passBy 方式: ' + passBy, () => {
      if (!fromPage) return;
      it('源页用 params 传参', () => {
        expect(fromPage.includes('params:') || fromPage.includes('params :')).toBe(true);
      });
    });

    describe('correct — 参数名一致', () => {
      if (!fromPage) return;
      it('参数 requestNo 在源页中传递', () => {
        expect(fromPage).toContain('requestNo');
      });
    });

    describe('correct — 返回导航', () => {
      if (!toPage) return;
      it('目标页可返回源页（提到了源路由名）', () => {
        expect(toPage).toContain('MerchantRefunds');
      });
    });
  });

  // ================================================================
  // Error: MerchantOrders → MerchantShipping — passBy 不匹配
  // ================================================================
  describe('error — MerchantOrders → MerchantShipping passBy 不匹配', () => {
    const fromPagePath = 'src/pages/merchant/orders/list.vue';
    const toPagePath   = 'src/pages/merchant/orders/shipping.vue';
    const passBy       = 'params';

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    describe('error — passBy 不匹配', () => {
      if (!fromPage) return;

      it('源页传参方式与预期不一致则参数丢失', () => {
        const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
        const hasParams = fromPage.includes('params:') || fromPage.includes('params :');

        if (passBy === 'params' && hasQuery && !hasParams) {
          fail('passBy 冲突: 预期 params 但源页用了 query');
        } else if (passBy === 'query' && hasParams && !hasQuery) {
          fail('passBy 冲突: 预期 query 但源页用了 params');
        }
      });
    });

    describe('error — 参数名不一致', () => {
      if (!fromPage || !toPage) return;

      it('源页和目标页的参数名应一致', () => {
        expect(fromPage).toContain('id');
        expect(toPage).toContain('id');
      });
    });
  });
});

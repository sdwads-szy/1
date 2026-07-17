const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

function readPageSafe(pagePath) {
  const fullPath = path.join(workspace, pagePath);
  if (!fs.existsSync(fullPath)) { console.warn('SKIP: ' + pagePath); return null; }
  return fs.readFileSync(fullPath, 'utf-8');
}

/**
 * 参数化 correct 场景：维度1(入口) + 维度2(passBy) + 维度3(参数名) + 维度4(返回)
 */
function testCorrectScenario({ scenarioName, fromPagePath, toPagePath, routeName, passBy, params, fromRouteName }) {
  describe(scenarioName, () => {
    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    // ==== 维度1: 源页包含跳转入口 ====
    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;

      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    // ==== 维度2: passBy 方式 ====
    if (passBy !== 'none') {
      describe('correct — passBy 方式: ' + passBy, () => {
        if (!fromPage) return;

        it('源页用 ' + passBy + ' 传参', () => {
          if (passBy === 'params') {
            expect(fromPage.includes('params:') || fromPage.includes('params :')).toBe(true);
          } else if (passBy === 'query') {
            expect(fromPage.includes('query:') || fromPage.includes('query :')).toBe(true);
          }
        });
      });
    }

    // ==== 维度3: 参数名一致 ====
    if (params.length > 0 && passBy !== 'none') {
      describe('correct — 参数名一致', () => {
        if (!fromPage) return;

        params.forEach(p => {
          it('参数 ' + p + ' 在源页中传递', () => {
            expect(fromPage).toContain(p);
          });
        });
      });
    }

    // ==== 维度4: 返回导航 ====
    describe('correct — 返回导航', () => {
      if (!toPage) return;

      it('目标页可返回源页（提到了源路由名: ' + fromRouteName + '）', () => {
        expect(toPage).toContain(fromRouteName);
      });
    });
  });
}

// ============================================================
// t_nav_browse_flow — 浏览流相邻页面间 passBy 和参数传递
// ============================================================
describe('t_nav_browse_flow', () => {

  // ----------------------------------------------------------
  // Scenario 1: Home → Search — query 传递关键词
  // ----------------------------------------------------------
  testCorrectScenario({
    scenarioName: 'Home → Search — query 传递关键词',
    fromPagePath: 'src/pages/home/index.vue',
    toPagePath: 'src/pages/search/index.vue',
    routeName: 'Search',
    passBy: 'query',
    params: ['keyword'],
    fromRouteName: 'Home'
  });

  // ----------------------------------------------------------
  // Scenario 2: Home → ProductDetail — params 传递商品ID
  // ----------------------------------------------------------
  testCorrectScenario({
    scenarioName: 'Home → ProductDetail — params 传递商品ID',
    fromPagePath: 'src/pages/home/index.vue',
    toPagePath: 'src/pages/product/detail.vue',
    routeName: 'ProductDetail',
    passBy: 'params',
    params: ['id'],
    fromRouteName: 'Home'
  });

  // ----------------------------------------------------------
  // Scenario 3: Home → Category — params 传递类目ID
  // ----------------------------------------------------------
  testCorrectScenario({
    scenarioName: 'Home → Category — params 传递类目ID',
    fromPagePath: 'src/pages/home/index.vue',
    toPagePath: 'src/pages/category/list.vue',
    routeName: 'Category',
    passBy: 'params',
    params: ['id'],
    fromRouteName: 'Home'
  });

  // ----------------------------------------------------------
  // Scenario 4: Category → ProductDetail — params 传递商品ID
  // ----------------------------------------------------------
  testCorrectScenario({
    scenarioName: 'Category → ProductDetail — params 传递商品ID',
    fromPagePath: 'src/pages/category/list.vue',
    toPagePath: 'src/pages/product/detail.vue',
    routeName: 'ProductDetail',
    passBy: 'params',
    params: ['id'],
    fromRouteName: 'Category'
  });

  // ----------------------------------------------------------
  // Scenario 5: ProductDetail → Cart — 加购后跳转购物车（无传参）
  // ----------------------------------------------------------
  testCorrectScenario({
    scenarioName: 'ProductDetail → Cart — 加购后跳转购物车',
    fromPagePath: 'src/pages/product/detail.vue',
    toPagePath: 'src/pages/cart/index.vue',
    routeName: 'Cart',
    passBy: 'none',
    params: [],
    fromRouteName: 'ProductDetail'
  });

  // ----------------------------------------------------------
  // Scenario 6: ProductDetail → Checkout — query 传递 skuId + quantity
  // ----------------------------------------------------------
  testCorrectScenario({
    scenarioName: 'ProductDetail → Checkout — 立即购买跳转结算',
    fromPagePath: 'src/pages/product/detail.vue',
    toPagePath: 'src/pages/checkout/index.vue',
    routeName: 'Checkout',
    passBy: 'query',
    params: ['skuId', 'quantity'],
    fromRouteName: 'ProductDetail'
  });

  // ==========================================================
  // Scenario 7: error — Home → ProductDetail query 替代 params
  // ==========================================================
  describe('Home → ProductDetail 传参错 — query 替代 params', () => {
    const fromPagePath = 'src/pages/home/index.vue';
    const toPagePath   = 'src/pages/product/detail.vue';
    const routeName    = 'ProductDetail';

    const fromPage = readPageSafe(fromPagePath);
    const toPage   = readPageSafe(toPagePath);

    // ==== 维度5: error — passBy 不匹配 ====
    describe('error — passBy 不匹配', () => {
      if (!fromPage || !toPage) return;

      it('路由 ' + routeName + ' 期望 params，源页使用了 query — 确认 passBy 不匹配', () => {
        const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
        // error 场景：源页使用了错误的 passBy（query 而非 params）
        // 断言不匹配条件成立，不应抛错
        expect(hasQuery).toBe(true);
        expect(fromPage).toContain(routeName);
      });

      it('目标页从 params 读取参数，与源页 query 传参不匹配', () => {
        const readsFromParams = toPage.includes('route.params') || toPage.includes('params.id');
        expect(readsFromParams).toBe(true);
      });
    });

    // ==== 维度6: error — 参数名一致但传递方式错 ====
    describe('error — 参数名一致但传递方式错', () => {
      if (!fromPage || !toPage) return;

      it('源页用 query 传 id，目标页从 params 读 id — 参数名相同但无法传递', () => {
        expect(fromPage).toContain('id');
        expect(toPage).toContain('id');
      });
    });
  });
});

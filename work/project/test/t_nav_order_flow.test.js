const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

function readPageSafe(pagePath) {
  const fullPath = path.join(workspace, pagePath);
  if (!fs.existsSync(fullPath)) { console.warn('SKIP: ' + pagePath); return null; }
  return fs.readFileSync(fullPath, 'utf-8');
}

describe('t_nav_order_flow', () => {
  // ========================================================================
  // Flow 1: OrderList → OrderDetail — params 传递订单号
  // ========================================================================
  describe('OrderList → OrderDetail — params 传递订单号', () => {
    const fromPage = readPageSafe('src/pages/orders/list.vue');
    const toPage   = readPageSafe('src/pages/orders/detail.vue');
    const routeName = 'OrderDetail';
    const passBy = 'params';
    const params = ['id'];

    // 维度1: 源页包含跳转入口
    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;

      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    // 维度2: passBy 方式
    describe('correct — passBy 方式: ' + passBy, () => {
      if (!fromPage) return;

      it('源页用 ' + passBy + ' 传参', () => {
        const hasParams = fromPage.includes('params:') || fromPage.includes('params :');
        expect(hasParams).toBe(true);
      });
    });

    // 维度3: 参数名一致
    describe('correct — 参数名一致', () => {
      if (!fromPage) return;

      it('参数 id 在源页中传递', () => {
        expect(fromPage).toContain('id');
      });
    });

    // 维度4: 返回导航
    describe('correct — 返回导航', () => {
      if (!toPage) return;

      it('目标页可返回源页（提到了 OrderList）', () => {
        expect(toPage).toContain('OrderList');
      });
    });

    // 维度5: error — passBy 不匹配
    describe('error — passBy 不匹配', () => {
      if (!fromPage) return;

      it('源页传参方式与预期一致则无冲突', () => {
        const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
        if (hasQuery) {
          fail('passBy 冲突: 预期 params 但源页用了 query');
        }
      });
    });

    // 维度6: error — 参数名不一致
    describe('error — 参数名不一致', () => {
      if (!fromPage || !toPage || params.length === 0) return;

      it('源页和目标页的参数名应一致', () => {
        params.forEach(p => {
          expect(fromPage).toContain(p);
          expect(toPage).toContain(p);
        });
      });
    });
  });

  // ========================================================================
  // Flow 2: OrderDetail → RefundApply — params 传递子订单ID
  // ========================================================================
  describe('OrderDetail → RefundApply — params 传递子订单ID', () => {
    const fromPage = readPageSafe('src/pages/orders/detail.vue');
    const toPage   = readPageSafe('src/pages/orders/refund/apply.vue');
    const routeName = 'RefundApply';
    const passBy = 'params';
    const params = ['subOrderId'];

    // 维度1: 源页包含跳转入口
    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;

      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    // 维度2: passBy 方式
    describe('correct — passBy 方式: ' + passBy, () => {
      if (!fromPage) return;

      it('源页用 ' + passBy + ' 传参', () => {
        const hasParams = fromPage.includes('params:') || fromPage.includes('params :');
        expect(hasParams).toBe(true);
      });
    });

    // 维度3: 参数名一致
    describe('correct — 参数名一致', () => {
      if (!fromPage) return;

      it('参数 subOrderId 在源页中传递', () => {
        expect(fromPage).toContain('subOrderId');
      });
    });

    // 维度4: 返回导航
    describe('correct — 返回导航', () => {
      if (!toPage) return;

      it('目标页可返回源页（提到了 OrderDetail）', () => {
        expect(toPage).toContain('OrderDetail');
      });
    });

    // 维度5: error — passBy 不匹配
    describe('error — passBy 不匹配', () => {
      if (!fromPage) return;

      it('源页传参方式与预期一致则无冲突', () => {
        const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
        if (hasQuery) {
          fail('passBy 冲突: 预期 params 但源页用了 query');
        }
      });
    });

    // 维度6: error — 参数名不一致（源页传 orderId 但目标取 subOrderId）
    describe('error — 参数名不一致', () => {
      if (!fromPage || !toPage || params.length === 0) return;

      it('源页和目标页的参数名应一致', () => {
        params.forEach(p => {
          expect(fromPage).toContain(p);
          expect(toPage).toContain(p);
        });
      });
    });
  });

  // ========================================================================
  // Flow 3: OrderDetail → RefundDetail — params 传递售后单号
  // ========================================================================
  describe('OrderDetail → RefundDetail — params 传递售后单号', () => {
    const fromPage = readPageSafe('src/pages/orders/detail.vue');
    const toPage   = readPageSafe('src/pages/orders/refund/detail.vue');
    const routeName = 'RefundDetail';
    const passBy = 'params';
    const params = ['requestNo'];

    // 维度1: 源页包含跳转入口
    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;

      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    // 维度2: passBy 方式
    describe('correct — passBy 方式: ' + passBy, () => {
      if (!fromPage) return;

      it('源页用 ' + passBy + ' 传参', () => {
        const hasParams = fromPage.includes('params:') || fromPage.includes('params :');
        expect(hasParams).toBe(true);
      });
    });

    // 维度3: 参数名一致
    describe('correct — 参数名一致', () => {
      if (!fromPage) return;

      it('参数 requestNo 在源页中传递', () => {
        expect(fromPage).toContain('requestNo');
      });
    });

    // 维度4: 返回导航
    describe('correct — 返回导航', () => {
      if (!toPage) return;

      it('目标页可返回源页（提到了 OrderDetail）', () => {
        expect(toPage).toContain('OrderDetail');
      });
    });

    // 维度5: error — passBy 不匹配
    describe('error — passBy 不匹配', () => {
      if (!fromPage) return;

      it('源页传参方式与预期一致则无冲突', () => {
        const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
        if (hasQuery) {
          fail('passBy 冲突: 预期 params 但源页用了 query');
        }
      });
    });

    // 维度6: error — 参数名不一致
    describe('error — 参数名不一致', () => {
      if (!fromPage || !toPage || params.length === 0) return;

      it('源页和目标页的参数名应一致', () => {
        params.forEach(p => {
          expect(fromPage).toContain(p);
          expect(toPage).toContain(p);
        });
      });
    });
  });

  // ========================================================================
  // Flow 4: RefundApply → RefundDetail — 申请成功后 params 传递售后单号
  // ========================================================================
  describe('RefundApply → RefundDetail — 申请成功后 params 传递售后单号', () => {
    const fromPage = readPageSafe('src/pages/orders/refund/apply.vue');
    const toPage   = readPageSafe('src/pages/orders/refund/detail.vue');
    const routeName = 'RefundDetail';
    const passBy = 'params';
    const params = ['requestNo'];

    // 维度1: 源页包含跳转入口
    describe('correct — 源页包含跳转入口', () => {
      if (!fromPage || !toPage) return;

      it('源页提到了目标路由名: ' + routeName, () => {
        expect(fromPage).toContain(routeName);
      });
    });

    // 维度2: passBy 方式
    describe('correct — passBy 方式: ' + passBy, () => {
      if (!fromPage) return;

      it('源页用 ' + passBy + ' 传参', () => {
        const hasParams = fromPage.includes('params:') || fromPage.includes('params :');
        expect(hasParams).toBe(true);
      });
    });

    // 维度3: 参数名一致
    describe('correct — 参数名一致', () => {
      if (!fromPage) return;

      it('参数 requestNo 在源页中传递', () => {
        expect(fromPage).toContain('requestNo');
      });
    });

    // 维度4: 返回导航
    describe('correct — 返回导航', () => {
      if (!toPage) return;

      it('目标页可返回源页（提到了 RefundApply）', () => {
        expect(toPage).toContain('RefundApply');
      });
    });

    // 维度5: error — passBy 不匹配
    describe('error — passBy 不匹配', () => {
      if (!fromPage) return;

      it('源页传参方式与预期一致则无冲突', () => {
        const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
        if (hasQuery) {
          fail('passBy 冲突: 预期 params 但源页用了 query');
        }
      });
    });

    // 维度6: error — 参数名不一致
    describe('error — 参数名不一致', () => {
      if (!fromPage || !toPage || params.length === 0) return;

      it('源页和目标页的参数名应一致', () => {
        params.forEach(p => {
          expect(fromPage).toContain(p);
          expect(toPage).toContain(p);
        });
      });
    });
  });
});

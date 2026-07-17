const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

function readPageSafe(pagePath) {
  const fullPath = path.join(workspace, pagePath);
  if (!fs.existsSync(fullPath)) { console.warn('SKIP: ' + pagePath); return null; }
  return fs.readFileSync(fullPath, 'utf-8');
}

describe('t_nav_cart_checkout_flow', () => {
  const pages = {
    cart: readPageSafe('src/pages/cart/index.vue'),
    checkout: readPageSafe('src/pages/checkout/index.vue'),
    pay: readPageSafe('src/pages/checkout/pay.vue'),
    orderDetail: readPageSafe('src/pages/orders/detail.vue'),
    orderList: readPageSafe('src/pages/orders/list.vue'),
  };

  // ==========================================
  // Flow 1: Cart → Checkout (passBy: none)
  // ==========================================
  describe('correct — Cart → Checkout', () => {
    const fromPage = pages.cart;
    const toPage = pages.checkout;
    const routeName = 'Checkout';

    it('Cart.vue 提到了目标路由名 Checkout', () => {
      if (!fromPage) return;
      expect(fromPage).toContain(routeName);
    });

    it('Checkout.vue 可返回 Cart 页（提到了 Cart 路由名）', () => {
      if (!toPage) return;
      expect(toPage).toContain('Cart');
    });
  });

  // ==========================================
  // Flow 2: Checkout → CheckoutPay (passBy: query, param: orderNo)
  // ==========================================
  describe('correct — Checkout → CheckoutPay', () => {
    const fromPage = pages.checkout;
    const toPage = pages.pay;
    const routeName = 'CheckoutPay';
    const passBy = 'query';
    const params = ['orderNo'];

    it('Checkout.vue 提到了目标路由名 CheckoutPay', () => {
      if (!fromPage) return;
      expect(fromPage).toContain(routeName);
    });

    it('Checkout.vue 用 query 传参', () => {
      if (!fromPage) return;
      expect(fromPage.includes('query:') || fromPage.includes('query :')).toBe(true);
    });

    it('参数 orderNo 在 Checkout.vue 中传递', () => {
      if (!fromPage) return;
      expect(fromPage).toContain('orderNo');
    });

    it('Pay.vue 可返回 Checkout 页（提到了 Checkout 路由名）', () => {
      if (!toPage) return;
      expect(toPage).toContain('Checkout');
    });
  });

  // ==========================================
  // Flow 3: CheckoutPay → OrderDetail (passBy: params, param: orderNo)
  // ==========================================
  describe('correct — CheckoutPay → OrderDetail', () => {
    const fromPage = pages.pay;
    const toPage = pages.orderDetail;
    const routeName = 'OrderDetail';
    const passBy = 'params';
    const params = ['orderNo'];

    it('Pay.vue 提到了目标路由名 OrderDetail', () => {
      if (!fromPage) return;
      expect(fromPage).toContain(routeName);
    });

    it('Pay.vue 用 params 传参', () => {
      if (!fromPage) return;
      expect(fromPage.includes('params:') || fromPage.includes('params :')).toBe(true);
    });

    it('参数 orderNo 在 Pay.vue 中传递', () => {
      if (!fromPage) return;
      expect(fromPage).toContain('orderNo');
    });

    it('OrderDetail.vue 可返回 CheckoutPay 页（提到了 CheckoutPay 路由名）', () => {
      if (!toPage) return;
      expect(toPage).toContain('CheckoutPay');
    });
  });

  // ==========================================
  // Flow 4: CheckoutPay → OrderList (passBy: none)
  // ==========================================
  describe('correct — CheckoutPay → OrderList', () => {
    const fromPage = pages.pay;
    const toPage = pages.orderList;
    const routeName = 'OrderList';

    it('Pay.vue 提到了目标路由名 OrderList', () => {
      if (!fromPage) return;
      expect(fromPage).toContain(routeName);
    });

    it('OrderList.vue 可返回 CheckoutPay 页（提到了 CheckoutPay 路由名）', () => {
      if (!toPage) return;
      expect(toPage).toContain('CheckoutPay');
    });
  });

  // ==========================================
  // Error: Checkout → CheckoutPay passBy 不匹配
  // ==========================================
  describe('error — Checkout → CheckoutPay passBy 不匹配', () => {
    const fromPage = pages.checkout;
    const toPage = pages.pay;
    const passBy = 'query';
    const params = ['orderNo'];

    it('Checkout.vue 传参方式应与预期一致 (query)', () => {
      if (!fromPage) return;
      const hasQuery = fromPage.includes('query:') || fromPage.includes('query :');
      const hasParams = fromPage.includes('params:') || fromPage.includes('params :');

      if (passBy === 'params' && hasQuery) {
        fail('passBy 冲突: 预期 params 但源页用了 query');
      } else if (passBy === 'query' && hasParams) {
        fail('passBy 冲突: 预期 query 但源页用了 params');
      }
    });

    it('Checkout.vue 和 Pay.vue 的参数名应一致', () => {
      if (!fromPage || !toPage || params.length === 0) return;
      params.forEach(p => {
        expect(fromPage).toContain(p);
        expect(toPage).toContain(p);
      });
    });
  });
});

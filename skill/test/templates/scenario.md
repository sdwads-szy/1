# scenario 层测试模板 — jest (CJS) + supertest

```js
const request = require('supertest');
const app = require('../../app');

describe('scenario: main trunk flow', () => {
  let token, orderId, paymentId;

  it('Step1: login -> token', async () => {
    const res = await request(app).post('/api/auth/login').send({ phone: 'testuser', password: 'Test123456' });
    expect(res.status).toBe(200);
    token = res.body.data.token;
  });

  it('Step2: browse products', async () => {
    const res = await request(app).get('/api/products?page=1');
    expect(res.status).toBe(200);
  });

  it('Step3: add to cart', async () => {
    const res = await request(app).post('/api/cart').set('Authorization', 'Bearer ' + token).send({ skuId: 1, quantity: 1 });
    expect(res.status).toBe(200);
  });

  it('Step4: create order -> orderId', async () => {
    const res = await request(app).post('/api/orders').set('Authorization', 'Bearer ' + token).send({ addressId: 1, cartItemIds: [1], payChannel: 'alipay' });
    expect(res.status).toBe(200);
    orderId = res.body.data.orderId;
    paymentId = res.body.data.paymentId;
  });

  // Step5: payment callback (mock external via nock)
  it('Step5: payment callback -> order.status becomes paid', async () => {
    const nock = require('nock');
    nock('https://api.payment.com').post('/callback').reply(200, { status: 'success' });
    // verify order.status updated
  });
});

// Branch scenario: depends on main trunk, only runs from fork point
describe('scenario: branch (depends on main trunk)', () => {
  // prefix already verified by main trunk -> pruned
  it('fork-point step', async () => { /* ... */ });
});
```

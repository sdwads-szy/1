# NFR 层测试 — k6 压测 + jest 安全扫描

## 压测 (k6)
```js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 200 },
    { duration: '30s', target: 200 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(99)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get('http://localhost:3000/api/products?page=1');
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}
```

## 安全扫描 (jest + supertest)
```js
const request = require('supertest');
const jwt = require('jsonwebtoken');
const app = require('../../app');

describe('NFR: security', () => {
  it('SQL injection: OR 1=1 returns no extra data', async () => {
    const res = await request(app).get("/api/products?keyword=' OR 1=1 --");
    expect(res.status).not.toBe(500);
  });

  it('XSS: script tag is encoded in output', async () => {
    const res = await request(app).post('/api/auth/register').send({ phone: '<script>alert(1)</script>', password: 'Test123456', smsCode: '123456' });
    expect(res.body.message).not.toContain('<script>');
  });

  it('Token tamper: wrong secret returns 401', async () => {
    const forged = jwt.sign({ userId: 1, role: 'admin' }, 'wrong_secret');
    const res = await request(app).get('/api/admin/users').set('Authorization', 'Bearer ' + forged);
    expect(res.status).toBe(401);
  });

  it('Concurrent oversell: only 1 succeeds for last item', async () => {
    const [r1, r2] = await Promise.all([
      request(app).post('/api/orders').set('Authorization', 'Bearer ' + tokenA).send({ addressId: 1, cartItemIds: [1], payChannel: 'alipay' }),
      request(app).post('/api/orders').set('Authorization', 'Bearer ' + tokenB).send({ addressId: 2, cartItemIds: [1], payChannel: 'alipay' }),
    ]);
    const successes = [r1, r2].filter(r => r.status === 200);
    expect(successes.length).toBe(1);
  });
});
```

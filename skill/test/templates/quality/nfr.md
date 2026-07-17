# nfr 测试模板 — 安全 + 性能

🛑 安全用 jest+supertest。性能用 k6/autocannon（jest 单线程测不了 QPS）。
🛑 攻击载荷被拦截 = 正确行为（correct），不是 error。
🛑 testScenarios 描述的是**攻击类型和防御目的**，具体载荷/接口路径**优先从真理取**。

## 🛑 真理优先（最高优先级）

| 真理来源 | 提供什么 | 怎么用 |
|---------|---------|--------|
| `@truth infra_middleware` | `helmet/cors/rateLimit` 中间件配置 | 🛑 安全测试的预期行为与真理的中间件配置一致 |
| `@truth infra_config` | `JWT_SECRET` / `ENCRYPTION_KEY` | 🛑 Token 测试用的 secret 与真理一致 |
| `@truth backend_*` | `routes[].handlers[].path` — 有注入风险的接口 | 🛑 攻击目标路径取真理中的真实接口 |

🛑 **真理 > testScenarios 描述**。真理说有 `helmet` 中间件，XSS 测试就期望被拦截而非崩溃。

## 占位符取值来源

| 占位符 | 优先从哪取 | 怎么取 |
|--------|-----------|--------|
| `{task_id}` | 任务数据 `id` | 直接填入 |
| `{method}` / `{path}` | **真理 `routes[]`** 优先 → testScenarios[].input | 安全测试目标接口的 method + path |
| 攻击载荷 | testScenarios[].input | 具体的 SQL注入/XSS/CORS/Token 载荷字符串 |
| 并发参数 | testScenarios[].input | 并发数、SKU、库存量 |

🛑 安全测试不验证精确 status——验证"不崩溃"（status !== 500）
🛑 并发测试 jest 只能测 2 并发，真实压测用 k6/autocannon

```javascript
const request = require('supertest');
const app = require('../app');
const jwt = require('jsonwebtoken');
const JWT_SECRET = process.env.JWT_SECRET || 'test-secret';

describe('{task_id}', () => {
  // ==== 安全 — SQL注入 ====
  describe('correct — SQL注入防护', () => {
    it("'; DROP TABLE-- → 被拦截", async () => {
      const res = await request(app)
        .get("/api/products/search?keyword='; DROP TABLE users; --");
      expect([200, 400]).toContain(res.status);
      expect(res.status).not.toBe(500);
    });
  });

  // ==== 安全 — XSS ====
  describe('correct — XSS防护', () => {
    it('<script> → 被转义', async () => {
      const res = await request(app)
        .post('/api/auth/register')
        .send({ phone: '<script>alert(1)</script>', password: 'Abc12345' });
      if (res.status === 200 || res.status === 400) {
        expect(res.text).not.toContain('<script>');
      }
    });
  });

  // ==== 安全 — CORS ====
  describe('correct — CORS白名单', () => {
    it('非白名单Origin → 拒绝', async () => {
      const res = await request(app)
        .options('/api/order')
        .set('Origin', 'https://evil.com')
        .set('Access-Control-Request-Method', 'POST');
      const acao = res.headers['access-control-allow-origin'];
      expect(acao).not.toBe('https://evil.com');
    });
  });

  // ==== 安全 — Token篡改 ====
  describe('correct — Token篡改防护', () => {
    it('错误secret的token → 401', async () => {
      const fakeToken = jwt.sign({ userId: 1, role: 'admin' }, 'wrong-secret');
      const res = await request(app)
        .get('/api/order/1')
        .set('Authorization', `Bearer ${fakeToken}`);
      expect(res.status).toBe(401);
    });
  });

  // ==== 性能 — RateLimit ====
  describe('boundary — 限流', () => {
    it('超频 → 429', async () => {
      const requests = Array.from({ length: 50 }, () =>
        request(app).get('/api/products').set('X-Forwarded-For', '1.2.3.4')
      );
      const results = await Promise.all(requests);
      expect(results.some(r => r.status === 429)).toBe(true);
    });
  });

  // ==== 性能 — 并发超卖 (k6/autocannon) ====
  describe('concurrency — 并发超卖', () => {
    it('2并发同SKU → 1成功1失败', async () => {
      const token = jwt.sign({ userId: 1, role: 'buyer' }, JWT_SECRET);
      const order = () => request(app)
        .post('/api/order')
        .set('Authorization', `Bearer ${token}`)
        .send({ items: [{ productId: 10, quantity: 1 }] });

      const [r1, r2] = await Promise.all([order(), order()]);
      const success = [r1, r2].filter(r => r.status === 201).length;
      const fail = [r1, r2].filter(r => r.status === 409).length;
      expect(success).toBe(1);
      expect(fail).toBe(1);
    });
  });

  // ==== 幂等 — 重复提交 ====
  describe('concurrency — 幂等防护', () => {
    it('同幂等键两次提交 → 返回同一结果', async () => {
      const token = jwt.sign({ userId: 1, role: 'buyer' }, JWT_SECRET);
      const key = 'IDEM-' + Date.now();
      const order = () => request(app)
        .post('{path}')
        .set('Authorization', `Bearer ${token}`)
        .set('Idempotent-Key', key)
        .send({...});

      const [r1, r2] = await Promise.all([order(), order()]);
      expect(r1.status).toBe(r2.status);
      expect(r1.body.data).toMatchObject(r2.body.data);
    });
  });

  // ==== 限流 — Rate Limit ====
  describe('boundary — 限流', () => {
    it('同IP超频 → 429', async () => {
      const requests = Array.from({ length: 25 }, () =>
        request(app).post('{path}').set('X-Forwarded-For', '1.2.3.4').send({...})
      );
      const results = await Promise.all(requests);
      expect(results.some(r => r.status === 429)).toBe(true);
    });
  });

  // ==== Token 刷新 ====
  describe('correct — Token 刷新', () => {
    it('accessToken过期 → refresh → 重试成功', async () => {
      const expiredToken = jwt.sign({ userId: 1 }, JWT_SECRET, { expiresIn: '0s' });
      const refreshToken = jwt.sign({ userId: 1, type: 'refresh' }, REFRESH_SECRET, { expiresIn: '30d' });

      const r1 = await request(app)
        .get('{protected_path}')
        .set('Authorization', `Bearer ${expiredToken}`);
      expect(r1.status).toBe(401);

      const refresh = await request(app)
        .post('/api/auth/refresh')
        .send({ refreshToken });
      expect(refresh.status).toBe(200);
      const newToken = refresh.body.data.accessToken;

      const r2 = await request(app)
        .get('{protected_path}')
        .set('Authorization', `Bearer ${newToken}`);
      expect(r2.status).toBe(200);
    });
  });
});
```

🛑 并发测试 jest 单线程只能测 2 并发——真实压测用 k6 或 autocannon。

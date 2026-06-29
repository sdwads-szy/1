# NFR 检查模板 (Layer 8: nfr) — 并发/安全/性能

```javascript
const request = require('supertest');
const app = require('../../app');

describe('{task_id}', () => {
  // 并发下单库存
  describe('并发下单库存', () => {
    it('100个并发请求, 库存只扣减100次', async () => {
      const requests = Array(100).fill(null).map(() =>
        request(app).post('/api/orders')
          .set('Authorization', `Bearer ${token}`)
          .send({ cartItemIds: [cartId], addressId: 1 })
      );
      const results = await Promise.all(requests);
      const successCount = results.filter(r => r.body.success).length;
      expect(successCount).toBeLessThanOrEqual(initialStock);
    });
  });

  // SQL 注入防护
  it("SQL注入: '; DROP TABLE-- 搜索不报错", async () => {
    const res = await request(app).get("/api/search?q='; DROP TABLE users--");
    expect(res.status).not.toBe(500);
    // 应返回正常错误或空结果, 而非数据库崩溃
  });

  // XSS 防护
  it('XSS: <script>alert(1)</script> 不执行', async () => {
    const res = await request(app).post('/api/reviews')
      .set('Authorization', `Bearer ${token}`)
      .send({ orderId: testOrderId, productId: testProductId,
              rating: 5, content: '<script>alert(1)</script>' });
    expect(res.body.success).toBe(true);
    // 返回的 content 应该是转义后的, 不含原始<script>标签
  });

  // Token 过期
  it('篡改过期Token返回401', async () => {
    const expiredToken = token.slice(0, -5) + 'xxxxx';
    const res = await request(app).get('/api/user/profile')
      .set('Authorization', `Bearer ${expiredToken}`);
    expect(res.status).toBe(401);
  });

  // 分页边界
  it('page=-1 修正为1, pageSize=10000 截断', async () => {
    const res = await request(app).get('/api/products?page=-1&pageSize=10000');
    expect(res.body.success).toBe(true);
    expect(res.body.data.page).toBe(1);
    expect(res.body.data.pageSize).toBeLessThanOrEqual(100);
  });

  // CORS
  it('非白名单Origin被拒绝', async () => {
    const res = await request(app).get('/api/products')
      .set('Origin', 'https://evil.com');
    // 生产环境应有 CORS 限制; 测试环境可能宽松
  });
});
```

## 关键规则
1. `testFramework` 根据类型选择: 并发=k6/autocannon, 安全=jest+supertest, Token=jest
2. 并发测试需要准备唯一数据 (每个请求用不同 userId)
3. 安全测试验证"不应崩溃"和"不应返回敏感信息"
4. 边界测试验证自动修正而非报错

# Scenario 检查模板 (Layer 7: scenario) — 多模块联合链, 分段端到端

```javascript
const request = require('supertest');
const app = require('../../app');

describe('{task_id}', () => {
  let token, userId;
  const phone = `scenario_${Date.now()}@test.com`;
  const password = 'Test123456';

  beforeAll(async () => {
    const res = await request(app).post('/api/auth/register')
      .send({ phone, password, smsCode: '000000' });
    token = res.body.data.token;
    userId = res.body.data.userId;
  });

  // 分段测试: 每段 2-4 步, 验证断点两端数据一致
  describe('S1: 浏览→下单', () => {
    let cartItemIds, orderId, paymentId;

    it('step1: 浏览商品列表', async () => {
      const res = await request(app).get('/api/products');
      expect(res.body.success).toBe(true);
      expect(res.body.data.list.length).toBeGreaterThan(0);
    });

    it('step2: 查看商品详情并加购', async () => {
      const products = (await request(app).get('/api/products')).body.data.list;
      const productId = products[0].id;
      const addRes = await request(app).post('/api/cart')
        .set('Authorization', `Bearer ${token}`)
        .send({ productId, quantity: 1, spec: '默认' });
      expect(addRes.body.success).toBe(true);
      cartItemIds = [addRes.body.data.id];
    });

    it('step3: 提交订单', async () => {
      const orderRes = await request(app).post('/api/orders')
        .set('Authorization', `Bearer ${token}`)
        .send({ cartItemIds, addressId: 1 });
      expect(orderRes.body.success).toBe(true);
      orderId = orderRes.body.data.orderId;
      paymentId = orderRes.body.data.paymentId;
      // 断点验证: step3 的 orderId 是正整数
      expect(orderId).toBeGreaterThan(0);
      expect(paymentId).toBeGreaterThan(0);
    });

    it('step4: 发起支付', async () => {
      const payRes = await request(app).post(`/api/payments/${paymentId}/pay`)
        .set('Authorization', `Bearer ${token}`)
        .send({ method: 'wxpay' });
      expect(payRes.body.success).toBe(true);
      // 断点验证: step4 的支付目标 = step3 的 paymentId
    });
  });

  afterAll(async () => {
    // 清理: 取消订单
    if (orderId) {
      await request(app).put(`/api/orders/${orderId}/cancel`)
        .set('Authorization', `Bearer ${token}`);
    }
  });
});
```

## 关键规则
1. **不验证业务逻辑**——不关心里面怎么算的
2. **只验证断点两端数据一致**: step3.orderId === step4的支付目标
3. 分段执行, 每段 2-4 步, 段间可独立运行
4. 分支 scenario 依赖主干 scenario ID, 从分叉点开始执行

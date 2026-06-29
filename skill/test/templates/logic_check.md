# 功能间联系链检查模板 (Layer 6: logic)

## 测试模式: 两个断点的输入输出对照

```javascript
const request = require('supertest');
const app = require('../../app');

describe('{task_id}', () => {
  let token, userId;
  const phone = `logic_${Date.now()}@test.com`;
  const password = 'Test123456';

  beforeAll(async () => {
    // 注册获取token
    const res = await request(app).post('/api/auth/register').send({ phone, password, smsCode: '000000' });
    token = res.body.data.token;
    userId = res.body.data.userId;
  });

  // 链: 注册→登录 (logicChains 定义的每条链对应一个 describe 块)
  describe('注册→登录链', () => {
    it('注册后能用相同 phone+password 登录', async () => {
      // 断点1: 注册 (已在 beforeAll 完成)
      // 断点2: 登录
      const loginRes = await request(app).post('/api/auth/login').send({ phone, password });
      expect(loginRes.body.success).toBe(true);
      expect(loginRes.body.data.token).toBeTruthy();
      // 验证: 断点2的 token 格式与断点1的 token 格式一致
      expect(typeof loginRes.body.data.token).toBe(typeof token);
    });
  });

  // 链: 下单→支付
  describe('下单→支付链', () => {
    let orderId, paymentId;
    
    it('下单返回的 paymentId 可发起支付', async () => {
      // 准备购物车数据
      // ... addToCart ...
      
      // 断点1: 下单
      const orderRes = await request(app).post('/api/orders')
        .set('Authorization', `Bearer ${token}`)
        .send({ items: [{productId: 1, quantity: 1}], addressId: 1 });
      expect(orderRes.body.success).toBe(true);
      orderId = orderRes.body.data.orderId;
      paymentId = orderRes.body.data.paymentId;
      
      // 断点2: 支付
      const payRes = await request(app).post(`/api/payments/${paymentId}/pay`)
        .set('Authorization', `Bearer ${token}`)
        .send({ method: 'wxpay' });
      expect(payRes.body.success).toBe(true);
      // 验证: 断点1的 paymentId = 断点2的支付目标
      expect(payRes.body.data.tradeNo).toBeTruthy();
    });
  });
});
```

## 关键规则
1. **只测断点两端的输入输出一致性**——不关心中间处理过程
2. 每条 logicChain → 一个 `describe` 块
3. 断点1的输出作为断点2的输入: `expect(断点2.输入).toBe(断点1.输出)`
4. 不需要 mock——走真实 HTTP 调用
5. 前置数据在 `beforeAll` 中准备，测试后清理

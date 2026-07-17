# logic 测试模板 — supertest 串联多模块

🛑 supertest 串联，每步 HTTP 请求。变量从响应提取传给下一步。
🛑 不验证单步内部逻辑（backend_proc真理），只验证跨步数据一致性。
🛑 testScenarios.process 描述的是**步骤链做什么**，具体路径/字段名**优先从真理取**。

## 🛑 mock/real 双模式

logic 测试走真实 HTTP 请求到后端，后端第三方服务用 `*_MODE=mock`。响应可能含 `mockHint` 字段：

```javascript
// 支付接口在 mock 模式下返回
// { success: true, data: { orderNo: 'xxx', mockHint: '模拟支付，回调已自动处理' } }
const r = await request(app).post('/api/orders/pay').send({...});
expect(r.status).toBe(201);
// mockHint 是 mock 模式的正常标记，不是错误
if (r.body.data.mockHint) {
  expect(r.body.data.mockHint).toBeDefined();
}
// 关键业务数据仍然正确
expect(r.body.data.orderNo).toEqual(expect.any(String));
```

🛑 **不要在测试中尝试调真实第三方 API**（如真实微信支付）
🛑 **不要因为 `mockHint` 断言失败**——它是 mock 模式的正常输出
🛑 **不要 mock 第三方 API 模块**——HTTP 请求走真实后端，后端自己处理 mock/real 切换

## 🛑 真理优先（🛑 只依赖 backend_proc 真理，不依赖 api/db_api）

### backend_proc 真理字段解读（prompt 中 `## 🛑 下层真理` 的 JSON）

| 字段 | 含义 | 怎么用 |
|------|------|--------|
| `services[].file` | Service 文件路径 | 定位服务 |
| `services[].functions[].name` | 已验证的服务函数名 | 🛑 函数名 |
| `services[].functions[].params` | 参数列表，如 `["phone:string","password:string"]` | 🛑 调用参数 |
| `services[].functions[].returns` | 返回值结构，如 `"{userId:number,token:string}"` | 🛑 步骤间变量提取字段名 |
| `services[].functions[].throws[]` | 🛑 精确错误码列表 | 异常场景断言 |
| `services[].functions[].transaction` | bool，是否有事务 | 验证 COMMIT/ROLLBACK |
| `services[].functions[].sql_queries[]` | SQL 实现细节 | 🆕 验证 DB 数据一致性 |
| `sql_queries[].query_order` | int，查询顺序号 | 步骤顺序 |
| `sql_queries[].table` | string，表名 | 数据一致性验证的表 |
| `sql_queries[].columns[]` | string[]，列名（DB 已验证） | 🛑 字段名来源 |
| `sql_queries[].connection` | pool/connection/transaction | 连接模式 |
| `sql_queries[].sql_params[]` | `?` 占位符参数 | SQL 参数名 |
| `services[].functions[].redis_ops[]` | Redis 操作（key/TTL） | 缓存验证 |
| `services[].functions[].env_dependent` | mock/real 行为差异 | mock 模式处理 |

### 场景字段解读

| `testScenarios[].process` | 步骤链：每步的 method + path + 做什么 | 🟡 方向 |
| `testScenarios[].output` | 期望结果 | 最终断言 |

🛑 **铁律：service 函数已由 backend_proc 验证通过。logic 只验证跨模块组合是否正确。所有字段名从 backend_proc 真理取。**

## 占位符取值来源

| 占位符 | 优先从哪取 | 怎么取 |
|--------|-----------|--------|
| `{task_id}` | 任务数据 `id` | 直接填入 |
| `{method1}` / `{method2}` | testScenarios[].process（api 层已验证过这些路由） | 小写 |
| `{path1}` / `{path2}` | testScenarios[].process（api 层已验证过这些路由） | 完整路径 |
| `{status1}` / `{status2}` | testScenarios[].output | 期望状态码 |
| `{id_field}` | 🛑 真理 `services[].returns` 优先 → testScenarios[].output | 步骤间传递的字段名 |
| `{expected_status}` | testScenarios[].output | 最终状态值 |
| `{field}` | **真理 DDL 列名** 优先 → testScenarios[].output | 需验证回滚的字段名 |
| `{compensation_path}` | testScenarios[].process 的补偿步骤 | 退款/取消接口路径 |
| `{verify_path}` | testScenarios[].process 的验证步骤 | 验证数据一致性的 GET 路径 |

```javascript
const request = require('supertest');
const app = require('../app');

describe('{task_id}', () => {
  let token;
  beforeAll(async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({ phone: '13800138000', password: 'Abc12345' });
    token = res.body.data.token;
  });

  // ==== 正向正常 — 多步串联数据一致 ====
  describe('correct — 数据协作', () => {
    it('{scenario}', async () => {
      // 步骤1
      const r1 = await request(app)
        .{method1}('{path1}')
        .set('Authorization', `Bearer ${token}`)
        .send({...});
      expect(r1.status).toBe({status1});
      const {id1} = r1.body.data.{id_field1};

      // 步骤2 — 使用步骤1的输出
      const r2 = await request(app)
        .{method2}('{path2}')
        .set('Authorization', `Bearer ${token}`)
        .send({ {id_field1}: id1, ... });
      expect(r2.status).toBe({status2});

      // 步骤3 — 验证跨步一致性
      const r3 = await request(app)
        .get(`{path3}/${id1}`)
        .set('Authorization', `Bearer ${token}`);
      expect(r3.status).toBe(200);
      expect(r3.body.data.status).toBe('{expected_status}'); // 状态已流转
    });
  });

  // ==== 正向异常 — 中间断点, 前面不受污染 ====
  describe('error — 断点不污染', () => {
    it('{scenario}', async () => {
      // 步骤1 正常
      const r1 = await request(app)
        .post('{path1}')
        .set('Authorization', `Bearer ${token}`)
        .send({...});
      expect(r1.status).toBe(201);
      const id = r1.body.data.{id_field};

      // 步骤2 失败
      const r2 = await request(app)
        .post('{path2}')
        .set('Authorization', `Bearer ${token}`)
        .send({ {id_field}: id, ... }); // 故意构造失败条件
      expect(r2.status).toBe(400);

      // 验证: 步骤1的副作用未被步骤2污染
      const verify = await request(app)
        .get(`{verify_path}/${id}`)
        .set('Authorization', `Bearer ${token}`);
      expect(verify.body.data.status).toBe('{original_status}'); // 保持原状态
    });
  });

  // ==== 边界 — 跨步数据边界 ====
  describe('boundary — 边界传递', () => {
    it('空值/零值在步骤间传递被拒绝', async () => {
      const r = await request(app)
        .post('{path1}')
        .set('Authorization', `Bearer ${token}`)
        .send({ quantity: 0 });
      expect(r.status).toBe(400);
    });
    it('超长/超大值在步骤间传递被拒绝', async () => {
      const r = await request(app)
        .post('{path1}')
        .set('Authorization', `Bearer ${token}`)
        .send({ quantity: 99999 });
      expect(r.status).toBe(400);
    });
  });

  // ==== 状态 — 跨步状态一致性 ====
  describe('state — 状态流转', () => {
    it('已完成状态拒绝后续操作', async () => {
      const r = await request(app)
        .post('{path2}')
        .set('Authorization', `Bearer ${token}`)
        .send({ id: '{completed_id}' });
      expect(r.status).toBe(409);
    });
  });

  // ==== 并发 — 乐观锁/库存竞态 ====
  describe('concurrency — 并发冲突', () => {
    it('并发写入产生冲突', async () => {
      const [r1, r2] = await Promise.all([
        request(app).post('{path1}').set('Authorization', `Bearer ${token}`).send({ quantity: 1 }),
        request(app).post('{path1}').set('Authorization', `Bearer ${token}`).send({ quantity: 1 }),
      ]);
      expect([r1.status, r2.status]).toContain(409);
    });
  });

  // ==== 反向正常 — 补偿流程 ====
  describe('correct — 补偿回滚', () => {
    it('{scenario}', async () => {
      // 先完成正向流程...
      // 执行补偿
      const refundRes = await request(app)
        .post('{compensation_path}')
        .set('Authorization', `Bearer ${token}`)
        .send({...});
      expect(refundRes.status).toBe(201);

      // 验证数据回滚
      const verify = await request(app)
        .get(`{verify_path}`)
        .set('Authorization', `Bearer ${token}`);
      expect(verify.body.data.{field}).toBe({original_value});
    });
  });

  // ==== 反向异常 — 补偿被拒 ====
  describe('error — 补偿被拒', () => {
    it('{scenario}', async () => {
      const res = await request(app)
        .post('{compensation_path}')
        .set('Authorization', `Bearer ${token}`)
        .send({...});
      expect(res.status).toBe(409);
    });
  });
});
```

# 后端处理检查模板 (Layer 4.5: backend_proc)

## 测试模式: HTTP请求 → 查数据库验证

```javascript
const request = require('supertest');
const app = require('../../app');
const db = require('../../config/db');

describe('{task_id}', () => {
  let token, userId;

  beforeAll(async () => {
    const phone = `proc_${Date.now()}@test.com`;
    const res = await request(app).post('/api/auth/register').send({ phone, password: 'Test123456', smsCode: '000000' });
    token = res.body.data.token;
    userId = res.body.data.userId;
  });

  // 场景: 数据落库 — 请求入参 → DB行验证
  it('POST /api/xxx 的数据正确写入数据库', async () => {
    // 发送请求
    const input = { /* testScenarios.given 推导 */ };
    const res = await request(app)
      .post('/api/xxx')
      .set('Authorization', `Bearer ${token}`)
      .send(input);
    expect(res.body.success).toBe(true);
    const resultId = res.body.data.id;

    // 查数据库验证: 主表有新行
    const rows = await db.query('SELECT * FROM target_table WHERE id = ?', [resultId]);
    expect(rows.length).toBe(1);

    // 验证关键字段值
    // testScenarios.then 中的每个预期转化为 expect(row.field).toBe(expectedValue)
  });

  // 场景: 关联表同步写入
  it('关联表同步写入', async () => {
    // 查关联表验证行数
    const related = await db.query('SELECT * FROM related_table WHERE parent_id = ?', [resultId]);
    expect(related.length).toBe(expectedCount);
  });

  // 场景: 响应字段与DB一致
  it('响应中的字段值与数据库实际写入一致', async () => {
    const dbRow = rows[0];
    // response.data.field === dbRow.field
    expect(res.body.data.someField).toBe(dbRow.some_field);
  });

  afterAll(async () => {
    // 清理测试数据
    await db.query('DELETE FROM target_table WHERE user_id = ?', [userId]);
  });
});
```

## 关键规则
1. **不验证业务逻辑**——不关心金额算没算对
2. **只验证数据管道**: HTTP请求字段 → DB列 → 响应字段 三者一致
3. `given` → 前置数据准备; `when` → HTTP请求; `then` → DB查询验证
4. 每个写操作端点(POST/PUT/DELETE)至少 1 个 `it()` 块
5. 测试后清理数据 (afterAll)

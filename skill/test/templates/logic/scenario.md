# scenario 测试模板 — 跨模块数据交接

🛑 2~4 步 supertest 短链，验证模块间**数据交接点**。beforeAll 准备前置状态。
🛑 不重测单步逻辑（logic 真理已验证），只测 A 模块产出 X → B 模块接收 X 的一致性。
🛑 **scenario 只依赖 logic + navigation 真理**。

## 🛑 真理优先

### 真理字段解读（prompt 中 `## 🛑 下层真理` 的 JSON）

**logic 真理** (`@truth t_logic_*`):
| 字段 | 含义 | 怎么用 |
|------|------|--------|
| `flows[].steps[].method` | HTTP 方法（GET/POST/PUT/DELETE） | 🛑 测试请求 method |
| `flows[].steps[].path` | 端点路径 | 🛑 测试请求 URL |
| `flows[].steps[].handler` | controller 函数名 | 定位源码 |
| `flows[].steps[].request_fields[]` | 请求 body 字段 | 🛑 请求 body 的 key |
| `flows[].steps[].returns` | 返回值结构 | 🛑 步骤间变量提取的字段名 |
| `flows[].steps[].throws[]` | 错误码列表 | 异常场景断言 |
| `flows[].handoff_fields[]` | 🆕 同层 peers 交接字段 | 🛑 下游可直接引用的字段名 |
| `flows[].handoff_example` | 🆕 交接字段示例值 | 🛑 beforeAll 测试数据 |

**navigation 真理** (`@truth t_nav_*`):
| 字段 | 含义 | 怎么用 |
|------|------|--------|
| `jumps[].passBy` | params/query/none | 🛑 页面传参方式 |
| `jumps[].params[]` | 参数名列表 | 🛑 参数名一致性 |
| `jumps[].routeName` | 路由名 | 页面跳转目标 |

### 场景字段解读

| `testScenarios[].process` | 全链路步骤 | 🟡 方向 |

🛑 **铁律：服务函数和页面跳转已验证通过。scenario 只验证端到端串联。**

## 占位符取值来源

| 占位符 | 优先从哪取 | 怎么取 |
|--------|-----------|--------|
| `{task_id}` | 任务数据 `id` | 直接填入 |
| `{path1}` / `{path2}` / ... | testScenarios[].process（api 层已验证） | 完整路径 |
| `{method}` | testScenarios[].process（api 层已验证） | 小写 |
| `{field}` | **真理 `response.fields`** 优先 → testScenarios[].output | 验证的字段名 |
| `{original_value}` | testScenarios[].output | 字段原始值 |
| `{expected_status}` | testScenarios[].output | 最终状态 |
| `{final_path}` | testScenarios[].process 最后一步 | 验证路径 |
| `{verify_path}` | testScenarios[].process 验证步骤 | 数据一致性 GET 路径 |
| `{reverse_path}` | testScenarios[].process 逆流程步骤 | 退款/取消路径 |
| `{missing_id}` | 编造 | 不存在的 id（如 99999） |

```javascript
const request = require('supertest');
const app = require('../app');

describe('{task_id}', () => {
  let token;

  beforeAll(async () => {
    // 从 t_db_user 真理获取种子用户直接登录（不注册新用户）
    // @truth t_db_user → exposed_to_upper.seed.users.test_users → [{id, phone, password, role}]
    const seedUsers = [{phone:'13800000001',password:'123456',role:'buyer'},{phone:'13800000002',password:'123456',role:'merchant'},{phone:'13800000003',password:'123456',role:'admin'}];
    const buyer = seedUsers.find(u => u.role === 'buyer');
    const login = await request(app).post('/api/auth/login').send({ phone: buyer.phone, password: buyer.password });
    token = login.body.data.token;
  });

  // ==== 交接点: A模块产出 → 处理逻辑 → B模块接收 ====
  describe('{handoff_name}', () => {
    it('[{category}] {scenario}', async () => {
      // 1. 模块A: 设置输入，验证输出
      const rA = await request(app)
        .{method_a}('{path_a}')
        .set('Authorization', `Bearer ${token}`)
        .send({...});
      expect(rA.status).toBe({status_a});
      const { {handoff_field} } = rA.body.data;

      // 2. 交接处理: 模块A输出 → 模块B输入
      const rB = await request(app)
        .{method_b}('{path_b}')
        .set('Authorization', `Bearer ${token}`)
        .send({ {handoff_field} });
      expect(rB.status).toBe({status_b});

      // 3. 验证: 模块B输出 = 模块A输出（交接一致性）
      expect(rB.body.data.{handoff_field}).toBe({handoff_field});
    });

    it('[{category}] {scenario}', async () => {
      // 1. 模块A: 正常产出
      const rA = await request(app)...;
      // 2. 交接失败: 模块B拒绝
      const rB = await request(app).send({ {handoff_field}: null });
      expect(rB.status).toBe(400);
      // 3. 模块A数据未被污染
      const verify = await request(app).get('{verify_path}');
      expect(verify.body.data.status).toBe('{original_status}');
    });
  });
});
        .post('{path3}')
        .set('Authorization', `Bearer ${token}`)
        .send({...});
      expect(r3.status).toBe(201);

      // ... 继续步骤4,5,6...

      // 最终: 全链路数据连贯性
      const final = await request(app)
        .get('{final_path}')
        .set('Authorization', `Bearer ${token}`);
      expect(final.status).toBe(200);
      // stock 已扣减 / status 已流转 / 关联数据一致
    });
  });

  // ==== 正向异常 — 中间断点, 后续不执行 ====
  describe('error — 断点中断', () => {
    it('{scenario}', async () => {
      // 正常走到第N步
      const rN = await request(app)
        .post('{path}')
        .set('Authorization', `Bearer ${token}`)
        .send({...}); // 故意触发失败条件
      expect(rN.status).toBe(400);

      // 验证: 前面步骤副作用未被污染
      const verify = await request(app)
        .get('{verify_path}')
        .set('Authorization', `Bearer ${token}`);
      expect(verify.body.data.{field}).toBe({original_value});
    });
  });

  // ==== 边界 — 长链边界 ====
  describe('boundary — 全链路边界', () => {
    it('首步失败，后续全部不可达', async () => {
      const r1 = await request(app).post('{path1}').send({}); // 空body
      expect(r1.status).toBe(400);
    });
    it('中间步骤超时/空响应', async () => {
      const r = await request(app).get('{path_with_missing_id}');
      expect(r.status).toBe(404);
    });
  });

  // ==== 状态 — 长链状态一致性 ====
  describe('state — 状态一致性', () => {
    it('全链路完成后所有关联状态一致', async () => {
      const r = await request(app)
        .get('{final_path}')
        .set('Authorization', `Bearer ${token}`);
      expect(r.body.data).toMatchObject({ status: '{expected_status}' });
    });
  });

  // ==== 反向正常 — 逆流程全链路 ====
  describe('correct — 逆流程', () => {
    it('{scenario}', async () => {
      // 先完成正向全链路...
      // 执行逆流程
      const reverse = await request(app)
        .post('{reverse_path}')
        .set('Authorization', `Bearer ${token}`)
        .send({...});
      expect(reverse.status).toBe(201);

      // 验证数据回滚到原位
      const verify = await request(app).get('{verify_path}');
      expect(verify.body.data.{field}).toBe({original_value});
    });
  });

  // ==== 反向异常 — 逆流程被拒 ====
  describe('error — 逆流程被拒', () => {
    it('{scenario}', async () => {
      const res = await request(app)
        .post('{reverse_path}')
        .set('Authorization', `Bearer ${token}`)
        .send({...});
      expect(res.status).toBe(409);
    });
  });
});
```

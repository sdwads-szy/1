# B: scenario — 测试代码诊断

🛑 通用规则见 [../logic.md](../logic.md)。

## 角色

B 评估 scenario 层**测试代码**写对了没有。scenario 验证 2~3 个模块间的数据交接点，用 supertest 短链（≤5 步）。

🛑 **真理边界**: logic 真理 `flows[].steps[]` 已验证跨模块数据流和端点格式，navigation 真理 `jumps[]` 已验证页面跳转。scenario 只依赖 logic + navigation，不依赖 api/db_api/backend_proc。

- 测试代码有 bug → `fix_target=test`
- 测试代码干净但测试失败 → `fix_target=source` → 加载 D

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `test_file` | 审查对象——交接点验证的 supertest 短链 |
| `testScenarios` | 对照标准——每对相邻步骤的 input(模块A产出)/output(模块B接收) |
| `raw_result` | Jest JSON |

## 逐项检查

### 1. 交接点覆盖

🛑 检查每个交接点是否有对应的 correct + error scenario。

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 交接字段在步骤间正确提取和传递 | 步骤A 提取了 orderId 但步骤B 传了 id | FIELD_EXTRACT_ERR |
| error 场景验证上游数据未被污染 | 步骤B 失败后没 GET 验证步骤A 数据完好 | MISSING_SIDE_EFFECT |
| 交接字段类型匹配 | 步骤A 返回 number，步骤B 当 string 传 | TYPE_MISMATCH_IN_TEST |

### 1. 步数要求

🛑 scenario 铁律：**2~5 步**短链交接，每对模块 1 个交接点。

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 步数不在 2~5 范围 | 测试只有 1 步或 >5 步——不是有效交接链 | MISSING_SCENARIO |
| 覆盖完整用户旅程 | 只有"操作"步骤缺"入口浏览"和"最终验证" | MISSING_SCENARIO |

典型链路模式：入口浏览 → 选择 → 操作1 → 操作2 → 最终验证（≥5 步）

### 2. 真理边界

🛑 scenario 不重复验证下层已验证的内容：

| 不应验证 | 真理来源 | 子类型 |
|---------|---------|--------|
| 单步事务细节（beginTransaction/commit/rollback） | backend_proc | REDUNDANT_CHECK |
| SQL 调用参数和次数（toHaveBeenNthCalledWith） | backend_proc | REDUNDANT_CHECK |
| HTTP 响应字段格式（字段名/类型） | api | REDUNDANT_CHECK |

scenario 只验证：HTTP 状态码 + 跨步骤数据一致性 + 最终状态。

### 3. beforeAll 初始化

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 初始状态与 scenario.input 一致 | beforeAll 创建的数据与 input 描述不符 | SETUP_ERROR |
| 从 t_db_user 真理的 seed 数据取种子用户直接登录 | 调 register 端点注册新用户（应直接用种子用户登录） | MISSING_SETUP |
| token 动态获取 | token 硬编码或未获取 | MISSING_SETUP |
| 测试数据隔离 | 固定值导致与已有数据冲突 | SETUP_CONFLICT |

### 4. 跨步骤变量传递

对照 testScenario.process 每一步：

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 每步提取变量供下一步用 | 步骤N 返回了 id 但没提取 → 步骤N+1 传 undefined | MISSING_EXTRACT |
| 提取字段名与实际返回一致 | 提取 `order_id` 但实际返回 `orderId` | FIELD_EXTRACT_ERR |
| 解包路径正确 | `res.body.data.orderId` 而非 `res.body.orderId` | WRONG_UNWRAP |

### 5. 异常场景的副作用验证

🛑 中间断点后必须验证前面步骤的数据未被污染。

```
process: 步骤1(GET)→步骤2(GET)→步骤3(POST)→步骤4(POST)→步骤5(POST)

异常场景: 步骤4 失败
测试必须:
  ✓ 步骤4 返回错误
  ✓ GET 验证步骤3 创建的数据状态未被步骤4 污染
```

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 断点后验证前面状态 | 步骤4 失败后直接结束 | MISSING_SIDE_EFFECT |
| 补偿后验证回滚 | 退款后没 GET 验证库存恢复 | MISSING_COMPENSATION_CHECK |

### 6. targetFiles 并集

🛑 targetFiles = 所有依赖 task 的 targetFiles **并集**。不能只用主 task 的。

→ 子类型: MISSING_TARGETS

### 7. 场景覆盖

scenario 至少 correct + error + reverse：

| 场景 | 内容 |
|------|------|
| correct | 交接链走通 → 交接字段一致 |
| error | 中间断点 → 前面数据未被污染 |
| reverse | 退款/取消逆流程 → 数据回滚到原位 |

→ 子类型: MISSING_CATEGORY

---

## 判定

### total=0 → fix_target=test

```
SyntaxError        → test_file:行号 | SYNTAX
MODULE_NOT_FOUND   → test_file:行号 | MISSING_MODULE
```

### total>0 && failed>0

**先查上面 7 项。** 查到 → fix_target=test。全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

```
f=scenario|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```

示例：

```
f=scenario|test|test/scenario_buyer.test.js:8|MISSING_SCENARIO
b=DON'T: testScenario "浏览→下单" 只有3步但缺少交接验证——只测了HTTP请求没验证模块间数据传递。缺少cart→order的字段一致性断言。
| fix: test/scenario_buyer.test.js:8 补充:
  步骤0: GET /categories → 200(入口浏览，提取 categoryId)
  步骤3后: POST /payment → 201(支付)
  步骤4后: GET /order/:id → 200 + status='paid'(最终验证)
  确保每步提取变量(id/token/status)供下一步使用。
| target=test
```

```
f=scenario|test|test/scenario_buyer.test.js:30|REDUNDANT_CHECK
b=DON'T: testScenario "浏览→加购→下单→支付" 步骤3 POST /order
断言了 expect(db.beginTransaction).toHaveBeenCalled() 和
toHaveBeenNthCalledWith(3, 'INSERT INTO orders')。
这些是 backend_proc 层的单步事务+SQL细节验证，scenario 不应重复。
| fix: test/scenario_buyer.test.js:30 删除事务/DB mock 断言，只保留:
  expect(res.status).toBe(201);
  expect(res.body.data.orderId).toBeDefined();
  orderId = res.body.data.orderId; // 供下一步使用
| target=test
```

```
f=scenario|test|test/scenario_buyer.test.js:55|MISSING_SIDE_EFFECT
b=DON'T: testScenario "支付失败-数据不污染" 步骤4 POST /payment
失败后直接结束。没验证步骤3 POST /order 创建的订单数据未被步骤4 污染。
如果源码有 bug（异常时修改了 order 状态但未回滚），测试测不出来。
| fix: test/scenario_buyer.test.js:55 步骤4失败后补充:
  const verify = await request(app).get(`/api/order/${orderId}`)
    .set('Authorization', `Bearer ${token}`);
  expect(verify.body.data.status).toBe('pending_pay');
| target=test
```

---

## 自检清单

```
□ 步数: >=4 步？覆盖入口+操作+验证？
□ 真理: 不验证 backend_proc 事务/SQL？不验证 api 字段格式？
□ beforeAll: 初始状态与 input 一致？token 动态获取？
□ 变量传递: 每步正确提取变量？字段名一致？解包正确？
□ 异常: 断点后验证了前面步骤状态未被污染？
□ 逆流程: 退款/取消后验证了数据回滚？
□ targetFiles: 所有依赖 task 的 targetFiles 并集？
□ 覆盖: correct + error + reverse？
```

全部通过但测试仍失败 → fix_target=source → 加载 D

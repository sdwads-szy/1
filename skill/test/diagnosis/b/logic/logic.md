# B: logic — 测试代码诊断

🛑 通用规则见 [../logic.md](../logic.md)。

## 角色

B 评估 logic 层**测试代码**写对了没有。logic 用 supertest 串联多个 API，验证跨功能数据一致性。走真实 HTTP 链路，不 mock DB。

- 测试代码有 bug → `fix_target=test`
- 测试代码干净但测试失败 → `fix_target=source` → 加载 D

🛑 **真理边界**: backend_proc 真理 `services[].functions[]` 已验证单步事务处理和端点格式（logic 只依赖 backend_proc）。logic 不重复验证单步内部逻辑。

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `test_file` | 审查对象——supertest 多步串联测试代码 |
| `testScenarios` | 对照标准——input(初始状态)/process(步骤链)/output(最终一致性) |
| `raw_result` | Jest JSON |

## 逐项检查

### 1. beforeAll 初始化

logic 测试必须在 beforeAll 中完成用户注册/登录，获取 token 供后续步骤使用。

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| beforeAll 存在且完整 | 缺 beforeAll，token 无处获取 | MISSING_SETUP |
| 注册/登录成功获取 token | 注册了但没从响应提取 token | MISSING_SETUP |
| 测试数据隔离 | 用了固定 phone 导致与已有数据冲突 | SETUP_CONFLICT |

### 2. 跨步骤变量传递

对照 testScenario.process，检查每一步是否正确提取变量传给下一步：

```
步骤1: POST /order → 201 + {orderId, status}
步骤2: POST /payment {orderId} → 使用步骤1的 orderId
```

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 变量提取字段名正确 | 步骤1 提取 `res.body.data.order_id` 但实际返回 `orderId` | FIELD_EXTRACT_ERR |
| 解包路径正确 | `res.body.data.orderId` 而非 `res.body.orderId` | WRONG_UNWRAP |
| 步骤间变量确实传递了 | 步骤1 提取了 orderId 但步骤2 没用到 | MISSING_EXTRACT |
| 变量类型匹配 | 步骤1 返回 number，步骤2 传给 parseInt 后变 string | TYPE_MISMATCH_IN_TEST |

### 3. 测试方式

🛑 logic 测试走**真实 HTTP 链路**（supertest），不应 mock DB。

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 无 jest.mock DB | 测试写了 `jest.mock('../../config/db')` | OVER_MOCK |
| 使用 supertest | 直接 require service 函数调 | WRONG_TEST_MODE |
| token 动态获取 | 硬编码 `const token = 'eyJ...'` | HARDCODED_TOKEN |

### 4. 步骤覆盖

对照 testScenario.process 的每一步：

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 每步都有对应的 it() 或请求 | process 4 步但测试只发了 3 个 HTTP 请求 | MISSING_STEP |
| 步骤顺序与 process 一致 | process 定义先下单再支付，测试反过来 | WRONG_ORDER |
| 每步都验证了 status + 关键字段 | 某步只发了请求没断言 | MISSING_ASSERT |

### 5. 异常场景的副作用验证

🛑 中间断点场景必须验证前面步骤的副作用未被污染。

```
process: 步骤1(创建)→步骤2(支付)→步骤3(查询)
异常: 步骤2 失败

测试必须验证:
  ✓ 步骤2 返回错误
  ✓ 步骤1 创建的数据状态未被步骤2 污染（GET 验证）
```

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 异常后验证前面状态 | 步骤2 失败后没 GET 验证步骤1 的数据仍然完好 | MISSING_SIDE_EFFECT |
| 补偿后验证数据回滚 | 退款后没 GET 验证库存恢复/状态回退 | MISSING_COMPENSATION_CHECK |

### 6. 场景覆盖

logic 至少 correct + error + compensation：

| 场景 | 内容 |
|------|------|
| correct | 多步串联全通 → 跨步数据一致 |
| error | 中间断点 → 前面步骤数据未被污染 |
| compensation | 退款/取消回滚 → 数据恢复到原位 |

→ 子类型: MISSING_CATEGORY

---

## 判定

### total=0 → fix_target=test

```
SyntaxError        → test_file:行号 | SYNTAX
MODULE_NOT_FOUND   → test_file:行号 | MISSING_MODULE
```

### total>0 && failed>0

**先查上面 6 项。** 查到 → fix_target=test。全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

```
f=logic|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```

示例：

```
f=logic|test|test/logic_payment.test.js:8|HARDCODED_TOKEN
b=DON'T: testScenario "下单→支付→查询" 走真实 HTTP，token 需动态获取。
测试硬编码 const token = 'eyJhbGciOi...'，此 token 可能已过期或
userId/role 与步骤1注册用户不匹配。
| fix: test/logic_payment.test.js:8 改为 beforeAll 动态获取:
  beforeAll(async () => {
    const res = await request(app).post('/api/login').send({phone, password});
    token = res.body.data.token;
  });
| target=test
```

```
f=logic|test|test/logic_payment.test.js:25|FIELD_EXTRACT_ERR
b=DON'T: testScenario "下单→支付" 步骤1 POST /order 返回
res.body.data = {orderId:42, status:'pending_pay'}，
但测试提取 const {order_id} = res.body.data，实际字段名是 orderId(camelCase)。
order_id 为 undefined → 步骤2 POST /payment 传了 undefined。
| fix: test/logic_payment.test.js:25 改为:
  const {orderId} = res.body.data;
| target=test
```

```
f=logic|test|test/logic_payment.test.js:50|MISSING_SIDE_EFFECT
b=DON'T: testScenario "支付失败-前面数据不受污染" 步骤2 POST /payment
失败后直接结束，没验证步骤1 创建的 order 数据未被污染。
如果源码有 bug（异常时未回滚但修改了状态），这个测试测不出来。
| fix: test/logic_payment.test.js:50 在步骤2失败后补充:
  const verify = await request(app).get(`/api/order/${orderId}`)
    .set('Authorization', `Bearer ${token}`);
  expect(verify.body.data.status).toBe('pending_pay'); // 保持原状态
| target=test
```

---

## 自检清单

```
□ beforeAll: 注册/登录获取 token？数据隔离？
□ 变量传递: 步骤间提取字段名正确？解包路径正确？确实传递了？
□ 测试方式: supertest 真实 HTTP？无 jest.mock DB？
□ token: beforeAll 动态获取？非硬编码？
□ 步骤覆盖: 每步都有请求+断言？顺序正确？
□ 异常: 中间断点后验证了前面步骤状态未被污染？
□ 补偿: 退款/取消后验证了数据回滚？
□ 场景: correct + error + compensation？
```

全部通过但测试仍失败 → fix_target=source → 加载 D

# B: backend_proc — 测试代码诊断

🛑 通用规则见 [../logic.md](../logic.md)。

## 角色

B 评估 backend_proc 层**测试代码**写对了没有。backend_proc 用 `jest.mock('../../config/db')` 模拟 DB，直接 require service 函数调用来验证单接口处理链。

- 测试代码有 bug → `fix_target=test`
- 测试代码干净但测试失败 → `fix_target=source` → 加载 D

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `test_file` | 审查对象——jest.mock DB + 直接调 service 的测试代码 |
| `testScenarios` | 对照标准——input(初始数据)/process(步骤链)/output(期望结果) |
| `raw_result` | Jest JSON |

## 逐项检查

### 1. Mock 基础设置

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 是否 jest.mock('../../config/db') | 忘了 mock DB，测试直接连真实数据库 | MISSING_MOCK |
| mock 了正确的模块路径 | `jest.mock('../../config/db')` 路径层级错 | MISSING_MODULE |
| 未 mock 不该 mock 的 | backend_proc 只 mock DB，不应 mock 其他 service | OVER_MOCK |
| 未调 HTTP | 用了 supertest/request(app)——backend_proc 直接调函数 | USED_HTTP_IN_PROC |

### 2. Mock 返回值

对照 testScenario.process 的每一步，检查 mock 返回值：

🛑 process 的每一步操作（SELECT/UPDATE/INSERT）都需要一个对应的 mockResolvedValueOnce。

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 返回值数量 = process 步骤数 | process 7 步但只设了 5 个 mockResolvedValueOnce | MOCK_SEQ_GAP |
| SELECT 返回值结构 | 应返回 `[[{stock:5}]]` 但 mock 返回了 `[{stock:5}]`（缺外层数组） | MOCK_RETURN_GAP |
| UPDATE 返回值含 affectedRows | mock 返回 `{}` 缺 `affectedRows` 字段 → 源码检查 affectedRows===0 走错分支 | MOCK_RETURN_GAP |
| INSERT 返回值含 insertId | mock 返回 `{}` 缺 `insertId` → 源码取 insertId 为 undefined | MOCK_RETURN_GAP |
| 返回值顺序与 process 一致 | SELECT 的值 mock 在了 UPDATE 之前？顺序打乱 | MOCK_ORDER_ERR |

### 3. toHaveBeenNthCalledWith 序号

🛑 process 步骤序号 = toHaveBeenNthCalledWith 的 n。步骤3 对应 n=3。

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 序号与 process 步骤对齐 | 步骤5 断言 n=4（因为跳过了某个步骤） | WRONG_NTH |
| SQL 字符串与 process 描述一致 | 断言 `'INSERT INTO orders'` 但 process 描述是 `'INSERT INTO order_items'` | WRONG_SQL_STRING |
| 参数与 process 描述一致 | process 描述传 `[userId, items]` 但断言传 `[userId, items[0]]` | WRONG_ARGS |

### 4. 事务断言

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 正向 it() 断言 commit 调用了 | 只断言了 query 调用，忘了 `expect(db.commit).toHaveBeenCalled()` | MISSING_COMMIT_ASSERT |
| 正向 it() 断言 rollback 未调用 | 忘了 `expect(db.rollback).not.toHaveBeenCalled()` | MISSING_NO_ROLLBACK |
| 异常 it() 断言 rollback 调用了 | 只断言了 `rejects.toThrow()`，忘了 `expect(db.rollback).toHaveBeenCalled()` | MISSING_ROLLBACK_ASSERT |
| 异常 it() 断言 commit 未调用 | 忘了 `expect(db.commit).not.toHaveBeenCalled()` | MISSING_NO_COMMIT |

### 5. 返回值断言

对照 testScenario.output，检查返回值断言：

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 字段名与 output 一致 | 断言 `result.order_id` 但 output 定义 `orderId` | FIELD_CASE_ERR |
| 字段类型与 output 一致 | output 定义 number 但断言 `.toBe('42')` | WRONG_TYPE |
| 覆盖 output 全部字段 | output 定义 5 个字段但只断言了 3 个 | MISSING_FIELD_ASSERT |

### 6. 场景覆盖

backend_proc 至少 correct + error + boundary + compensation：

| 场景 | 内容 |
|------|------|
| correct | 事务完整走通 → commit → 返回值正确 |
| error | 中间断点 → rollback → 错误码正确 |
| boundary | 空值/零值/负值被拒绝 |
| state | 非法状态转换被拒绝（已完成/已取消不可再操作） |
| compensation | 补偿事务走通（退款→库存恢复） |
| compensation error | 补偿被拒（已退款再退→409） |

→ 子类型: MISSING_CATEGORY

---

## 判定

### total=0 → fix_target=test

```
SyntaxError        → test_file:行号 | SYNTAX
MODULE_NOT_FOUND   → test_file:行号 | MISSING_MODULE
jest.mock 不完整    → test_file:行号 | MISSING_MOCK
```

### total>0 && failed>0

**先查上面 6 项。** 查到 → fix_target=test。全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

```
f=backend_proc|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```

示例：

```
f=backend_proc|test|test/order.test.js:25|MOCK_SEQ_GAP
b=DON'T: testScenario "下单扣库存" process 共7步(BEGIN→SELECT→UPDATE→
INSERT orders→INSERT items→COMMIT→返回)，测试只设了4个 mockResolvedValueOnce，
缺步骤5(INSERT order_items)和步骤6(COMMIT)的返回值。
导致 toHaveBeenNthCalledWith(5) 断言时 mock 只有4个值。
| fix: test/order.test.js:25 在第4个 mock 后补充:
  db.query.mockResolvedValueOnce({ insertId: 200, affectedRows: 1 }); // 步骤5
  db.query.mockResolvedValueOnce(undefined); // 步骤6 COMMIT
| target=test
```

```
f=backend_proc|test|test/order.test.js:30|MOCK_RETURN_GAP
b=DON'T: testScenario "下单扣库存" process 步骤3 UPDATE 后期望
检查 affectedRows===0 决定是否 throw。但测试 mock UPDATE 返回值
为 {}（空对象），源码 `if (result.affectedRows === 0)` 中
result.affectedRows 为 undefined === 0 为 false，走不到异常分支。
| fix: test/order.test.js:30 改为:
  db.query.mockResolvedValueOnce([{ affectedRows: 1 }]);
| target=test
```

```
f=backend_proc|test|test/order.test.js:45|MISSING_ROLLBACK_ASSERT
b=DON'T: testScenario "库存不足回滚" error 场景，测试断言了
rejects.toThrow('INSUFFICIENT_STOCK')，但没断言 rollback 被调用。
如果源码 catch 块忘了 rollback，这个测试测不出来。
| fix: test/order.test.js:45 补充:
  await expect(createOrder(...)).rejects.toThrow('INSUFFICIENT_STOCK');
  expect(db.rollback).toHaveBeenCalled();
  expect(db.commit).not.toHaveBeenCalled();
| target=test
```

---

## 自检清单

```
□ Mock 基础: jest.mock('../../config/db') 存在、路径正确？
□ 未 mock 其他模块、未调 HTTP？
□ 返回值数量: mockResolvedValueOnce 数量 = process 步骤总数？
□ 返回值结构: SELECT 含 [[{...}]]、UPDATE 含 affectedRows、INSERT 含 insertId？
□ 返回值顺序: 与 process 步骤顺序一致？
□ 序号: toHaveBeenNthCalledWith(n) 的 n = process 步骤序号？
□ 事务: 正向断言 commit+!rollback，异常断言 rollback+!commit？
□ 返回值: 字段名与 output 一致？类型正确？全部字段覆盖？
□ 场景: correct + error + boundary + state + compensation 齐全？ 补偿事务 + 补偿被拒都有？
```

全部通过但测试仍失败 → fix_target=source → 加载 D

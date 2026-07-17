# B: 逻辑层 — 测试代码诊断

适用于: backend_proc / logic / scenario。

🛑 各层的特定检查项见对应文件：[backend_proc](logic/backend_proc.md)、[logic](logic/logic.md)、[nfr](logic/nfr.md)、[scenario](logic/scenario.md)。

## 角色

B 的职责：对照 **testScenarios + 下层真理** 判断**测试代码**是否正确。🛑 **不读源码**——源码分析由 D 步骤负责。

```
测试断言 vs 真理值 → 一致？ → 测试正确 → fix_target=source（C 修源码）
测试断言 vs 真理值 → 不一致？ → 测试写错 → fix_target=test（A 修测试）
```

🛑 **判断依据**：
- 精确值（handler名、错误码、字段名、返回值形状）→ **下层真理** 是权威
- 业务流程方向 → **testScenarios** 是参考
- testScenarios 写 `add` 但真理写 `addToCart` → 测试断言 `addToCart` 是对的，真理优先
- 🛑 B 不需要读源码来判断——对比测试断言和真理值就能判断谁错了

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `## 🛑 下层真理` | 🛑 **精确值的权威来源**——handler名/错误码/字段名/返回值形状 |
| `## 🛑 测试场景` | 流程方向参考——input/process/output 的业务含义 |
| `test_file` | 审查对象——A 生成的测试代码（只看这个文件，不读源码） |
| `raw_result` | Jest JSON——哪个 it() 过了、哪个没过 |
| 🛑 **不读源码** | 源码分析由 D 负责。B 只对比测试断言 vs 真理值 |

## 判定流程

### total=0 — 测试没跑起来

```
SyntaxError        → fix_target=test | SYNTAX
MODULE_NOT_FOUND   → fix_target=test | MISSING_MODULE
jest.mock 不完整    → fix_target=test | MOCK_GAP
```

测试自身有语法/加载/mock 错误，修测试代码。

### total>0 && failed>0

**先查测试代码。** 对照 testScenarios 逐项检查（具体检查项见各层文件）：

- backend_proc: mock 返回值/序号/事务断言
- logic: beforeAll/变量传递/测试方式
- nfr: 载荷强度/期望值/并发方式
- scenario: 步数/真理边界/副作用验证

查到问题 → fix_target=test。全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

```
f={layer}|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```

🛑 b 必须含文件:行号。fix 中的代码完整可执行，不含 `...` 或占位符。

示例：

```
f=backend_proc|test|test/order.test.js:25|MOCK_GAP
b=DON'T: testScenario "下单扣库存" process 共7步，测试只设了4个
mockResolvedValueOnce，缺步骤5(INSERT order_items)和步骤6(COMMIT)的返回值。
| fix: test/order.test.js:25 在第4个 mock 后补充:
  db.query.mockResolvedValueOnce({insertId:200, affectedRows:1}); // 步骤5
  db.query.mockResolvedValueOnce(undefined); // 步骤6
| target=test
```

```
f=logic|test|test/logic_payment.test.js:25|FIELD_EXTRACT_ERR
b=DON'T: testScenario "下单→支付" 步骤1 返回 {orderId:42}，
测试提取 const {order_id} = res.body.data，实际字段名是 orderId。
| fix: test/logic_payment.test.js:25 改为 const {orderId} = res.body.data;
| target=test
```

```
f=scenario|test|test/scenario_buyer.test.js:8|MISSING_SCENARIO
b=DON'T: testScenario "浏览→下单" 缺少交接验证——只测了HTTP请求没验证cart→order的数据传递。
| fix: 补充分 cart.items[0].productName/price/quantity = GET /order/:id items[0] 对应字段
| target=test
```

---

## Ban 质量等级

| 等级 | 表现 | A 能直接修复？ |
|------|------|:---:|
| **L2 可用** | 指出测试哪里错了（如"mock 有问题"） | ⚠️ 需自己找具体代码 |
| **L3 精确** | L2 + 文件:行号 + 完整修正代码 | ✅ |
| **L4 完整** | L3 + 解释为什么原测试代码是错的 | ✅✅ |

**目标：所有 ban 达到 L3 以上。**

---

## 子类型枚举

| 子类型 | 含义 | 常见于 |
|--------|------|--------|
| SYNTAX | 测试代码语法错误 | 全部 |
| MISSING_MODULE | require 路径错或模块不存在 | 全部 |
| MOCK_GAP | jest.mock 不完整或缺失 | backend_proc |
| MOCK_RETURN_GAP | mock 返回值缺字段（affectedRows/insertId） | backend_proc |
| MOCK_SEQ_GAP | mockResolvedValueOnce 数量不足 | backend_proc |
| MOCK_ORDER_ERR | mock 返回值顺序与 process 不对应 | backend_proc |
| WRONG_NTH | toHaveBeenNthCalledWith 序号错 | backend_proc |
| WRONG_SQL_STRING | 断言的 SQL 字符串与 process 不一致 | backend_proc |
| MISSING_ROLLBACK_ASSERT | 异常 it() 缺 rollback 断言 | backend_proc |
| MISSING_COMMIT_ASSERT | 正向 it() 缺 commit 断言 | backend_proc |
| MISSING_SETUP | beforeAll 缺注册/登录获取 token | logic, scenario |
| FIELD_EXTRACT_ERR | 步骤间变量提取字段名与实际返回不一致 | logic, scenario |
| WRONG_UNWRAP | 响应解包路径错 | logic, scenario |
| HARDCODED_TOKEN | token 硬编码而非动态获取 | logic |
| OVER_MOCK | mock 了不该 mock 的模块 | logic, scenario |
| MISSING_EXTRACT | 跨步骤变量未提取传递 | logic, scenario |
| MISSING_SIDE_EFFECT | 异常断点后缺前面步骤的副作用验证 | logic, scenario |
| WRONG_TEST_MODE | 测试方式与层级不匹配 | logic |
| WEAK_PAYLOAD | 攻击载荷太弱/不标准 | nfr |
| SEQUENTIAL_CONCURRENT | 并发测试用 await 顺序发 | nfr |
| WRONG_TEST_DATA | 测试数据量不足（如 RateLimit 只发 5 请求） | nfr |
| WRONG_EXPECT | 期望值与 category 冲突 | nfr |
| MISSING_SCENARIO | 步数不足或场景不完整 | scenario |
| REDUNDANT_CHECK | 验证了下层真理已验证的内容 | scenario |
| MISSING_TARGETS | targetFiles 未取依赖 task 并集 | scenario |
| MISSING_CATEGORY | 缺某个场景覆盖 | 全部 |
| MISSING_REAL_PATH | 只有 mock 路径缺少 real 实现 | backend_proc, logic |
| HARDCODED_API_KEY | real 路径硬编码了 API 密钥 | backend_proc, logic |
| MOCK_FLAGGED_AS_ERROR | 把 mockHint 误判为错误 | logic, scenario |

---

## 🛑 mock/real 判定铁律

| 现象 | 判定 |
|------|------|
| 响应含 `mockHint` 且 HTTP 状态码正确 | ✅ 正常——mock 模式下的预期行为 |
| 只有 mock 路径，real 路径被注释/为空 | ❌ MISSING_REAL_PATH → fix_target=source |
| real 路径硬编码 API 密钥 | ❌ HARDCODED_API_KEY → fix_target=source |
| 测试因为 `mockHint` 字段断言失败 | ❌ MOCK_FLAGGED_AS_ERROR → fix_target=test |
| 测试尝试调真实第三方 API 导致超时/连接失败 | ❌ fix_target=test——logic 层不测真实外部 API |

---

## 🛑 最终响应（JSON 必须用 `<!--FINAL-->` 包裹）

**B 只输出 ban——测试代码有问题时：**
```
<!--FINAL-->
[
  {"f": "{layer}|test|{file}:{行号}|{子类型}", "b": "DON'T: {问题} — {为什么} | fix: {文件}:{行号} {完整修正代码} | target=test"}
]
<!--FINAL-->
```
🛑 每条 ban 必须含文件:行号 + 完整修正代码（L3 以上）。
🛑 同根因合并：多个 it() 同一问题 → 合并为 1 条 ban。
🛑 输出后立即停止，不要再调工具。

## 自检清单

```
□ 只读了测试代码 + 测试输出 + 真理，没读源码？
□ 判断依据是对比"测试断言 vs 真理值"，不是"测试断言 vs 源码"？
□ 精确值以真理为准，testScenarios 只是方向参考？
□ ban 含文件:行号 + 完整修正代码（L3 以上）？
□ backend_proc: mock 返回值含 affectedRows/insertId？
□ logic: token 动态获取、走真实 HTTP？
□ nfr: 攻击载荷被拦截=correct（不期望500）？
□ scenario: 步数>=4、不验证 backend_proc 真理？
```

全部通过但测试仍失败 → fix_target=source → 加载 D

---

## 真理产出（测试通过时）

🛑 测试全部通过（total>0 && failed==0）→ 本层验证完成，产出真理：

| 子层 | 产出 key | 见 |
|------|---------|-----|
| backend_proc | `services` | truths/backend_proc.md |
| logic | `flows` | truths/logic.md |
| scenario | `chains` | truths/scenario.md |

格式见 `skill/test/truths/{子层}.md`。

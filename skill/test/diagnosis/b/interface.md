# B: 接口层 — 测试代码诊断

适用于: api / auth / db_api / navigation。

🛑 各层的特定检查项见对应文件：[api](interface/api.md)、[auth](interface/auth.md)、[db_api](interface/db_api.md)、[navigation](interface/navigation.md)。

## 角色

B 的职责：对照 `## 🛑 测试场景` 判断**测试代码**和**源码**谁有问题。

```
测试代码 vs testScenarios → 不一致？ → fix_target=test（A 写错了）
测试代码 = testScenarios 但源码不符 → fix_target=source（C 补功能）
```

🛑 **testScenarios 的定位**：
- `scenario` 名和 `category` → 测什么方向（真实期望）
- `output` 中的字段值 → **示例/参考**，不是精确断言值
- 🛑 精确值（handler名、路径、错误码）以**下层真理**为准（`@truth t_frontend_*` exports key, `@truth t_api_*` handlers），不以 testScenarios 为准

**判断时**：如果 testScenarios 写 `add` 但真理 exports key 是 `addToCart`，测试断言 `addToCart` 是对的。不要因为测试 ≠ testScenarios 的字面值就判 test_bug。

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `## 🛑 测试场景` | 🛑 诊断标准——期望的 input/output。对照它判断测试代码是否正确、源码是否缺功能 |
| `test_file` | 审查对象——A 生成的测试代码 |
| `testScenarios` | 对照标准——input(触发条件)/output(期望结果)/category(验证维度) |
| `raw_result` | Jest JSON——哪个 it() 过了、哪个没过 |

## 判定流程

### total=0 — 测试没跑起来

```
SyntaxError        → fix_target=test | SYNTAX
MODULE_NOT_FOUND   → fix_target=test | MISSING_MODULE
```

测试自身有语法/加载错误，修测试代码。

### total>0 && failed>0

**先查测试代码。** 对照 testScenarios 逐项检查（具体检查项见各层文件）。

查到问题 → fix_target=test。全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

🛑 **指纹铁律**: 测试问题 `f=` 第二段必须是 `test`，源码问题才是 `source`。
  - `fix_target=test` → `f=api|test|test/xxx.test.js:行号|SUBTYPE`
  - `fix_target=source` → `f=api|source|routes/xxx.js:行号|SUBTYPE`
🛑 禁止混用！用错会导致调度器跳过正确的修复步骤。

```
f={layer}|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```

🛑 b 必须含文件:行号。fix 中的代码完整可执行，不含 `...` 或占位符。

示例：

```
f=api|test|test/api/order.test.js:15|WRONG_STATUS
b=DON'T: testScenario "缺必填字段" category=error，
测试断言 expect(res.status).toBe(200)。error 场景应返回 400。
| fix: test/api/order.test.js:15 改为:
  expect(res.status).toBe(400);
  expect(res.body.message).toMatch(/items/i);
| target=test
```

```
f=auth|test|test/auth_token.test.js:5|USED_HTTP_IN_AUTH
b=DON'T: testScenario "jwt.sign产出三段式token" 测试 require('../../app')
使用 supertest。token 测试应纯 JWT（直接调 jwt.sign+jwt.verify）。
| fix: test/auth_token.test.js:5 改为:
  const jwt = require('jsonwebtoken');
  const token = jwt.sign({userId:1, role:'buyer'}, JWT_SECRET, {expiresIn:'24h'});
  expect(token.split('.').length).toBe(3);
| target=test
```

```
f=navigation|test|test/nav_order.test.js:10|VERIFIED_TRUTH
b=DON'T: testScenario "passBy方式一致" 测试用 fs.existsSync 检查
.vue 文件是否存在。这是 frontend 真理，navigation 只验证跳转逻辑。
| fix: 删除 fs.existsSync，改为验证 push 方式 + route 动态段 + 参数名一致
| target=test
```

---

## Ban 质量等级

| 等级 | 表现 | A 能直接修复？ |
|------|------|:---:|
| **L2 可用** | 指出测试哪里错了（如"状态码不对"） | ⚠️ 需自己找具体代码 |
| **L3 精确** | L2 + 文件:行号 + 完整修正代码 | ✅ |
| **L4 完整** | L3 + 解释为什么原测试代码是错的 | ✅✅ |

**目标：所有 ban 达到 L3 以上。**

---

## 子类型枚举

| 子类型 | 含义 | 常见于 |
|--------|------|--------|
| SYNTAX | 测试代码语法错误 | 全部 |
| MISSING_MODULE | require 路径错或模块不存在 | 全部 |
| WRONG_METHOD | HTTP 方法与 scenario.input 不一致 | api |
| WRONG_PATH | 请求路径与 scenario.input 不一致 | api |
| WRONG_STATUS | 状态码断言与 category 不匹配 | api |
| WRONG_FIELD | 断言字段名与 output 不一致 | api |
| WRONG_RESPONSE_PATH | 响应解包路径错（res.body vs res.body.data） | api |
| HARDCODED_TOKEN | Token 硬编码而非 jwt.sign 生成 | api, logic |
| USED_HTTP_IN_AUTH | auth 层使用了 supertest（应纯 JWT） | auth |
| MISSING_PAYLOAD_IN_TEST | jwt.sign payload 缺字段 | auth |
| WRONG_EXPIRY_TEST | 过期 token 测试方式错误 | auth |
| HTTP_IN_STATIC_CHECK | 静态检查用了 HTTP 请求 | auth |
| WRONG_DDL_PATH | DDL 路径编造而非用 t_db_* 真理 | db_api |
| COLUMN_SPELLING_ERR | toContain 列名拼写与 DDL 不一致 | db_api |
| VERIFIED_TRUTH | 验证了下层真理已验证的内容（不含 db_api 的 boundary 约束检查） | navigation |
| WRONG_SRC_PATH | fs.readFileSync 路径与项目实际不一致 | navigation, auth, db_api |
| INCOMPLETE_CHECK | 只验证了一端（如只查 push 没查 route 定义和参数读取） | navigation |
| MISSING_CATEGORY | 缺某个 category 的 describe 块 | 全部 |
| OVER_MOCK | mock 了不该 mock 的模块 | api |
| MISSING_TAMPER_CASE | 缺篡改 payload 验签失败测试 | auth |
| MISSING_REFRESH_CROSS_USE | 缺 refresh_token 当 access_token 用的边界测试 | auth |
| MISSING_EMPTY_PAYLOAD | 缺 payload 空对象 boundary 测试 | auth |
| COLUMN_COUNT_MISMATCH | INSERT 列数与 VALUES 数不匹配未检查 | db_api |
| MISSING_TX_MISUSE_CHECK | 缺事务内误用 db.query() 检查 | db_api |
| MISSING_REAL_PATH | 只有 mock 路径缺少 real 实现 | api, logic |
| HARDCODED_API_KEY | real 路径硬编码了 API 密钥而非 process.env | api, logic |

---

## 🛑 mock/real 双模式判定

源码中 `*_MODE` + `if (MODE === 'mock')` 是**合法的双路径模式**，不是缺陷。

| 现象 | 判定 |
|------|------|
| mock 和 real 路径都有完整实现 | ✅ 正确，不报 ban |
| 只有 mock 路径，real 路径为空/注释 | ❌ MISSING_REAL_PATH，fix_target=source |
| real 路径硬编码 API 密钥（`apiKey: 'sk-xxx'`） | ❌ HARDCODED_API_KEY，fix_target=source |
| 测试断言了 real 路径的 API 调用细节 | ❌ 测试不应依赖真实 API 行为，fix_target=test |

🛑 **判定铁律**：看到源码有 `_MODE` 检查 → 这是设计意图，不是 bug。只报确实缺失的（real 路径为空、密钥硬编码）。

---

## 🛑 真理绝对权威

prompt 中 `## 🛑 下层真理` 列出了依赖工程师已验证的接口（列名/路由/字段/函数签名）。

🛑 **真理 > 测试断言 > 诊断猜测**。判断 target 前必须先对照真理：
- 测试断言与真理冲突 → **测试错了**，fix_target=test
- 测试断言与真理一致但测试失败 → **源码错了**，fix_target=source
- 不确定时 → 真理为准。真理经过了工程师+测试双重验证，不可质疑

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
□ 先查测试代码——而非直接跳到源码分析？
□ 对照 testScenarios 逐项检查了请求/断言/字段名？
□ ban 含文件:行号 + 完整修正代码？
□ auth 测试未使用 supertest？
□ navigation 测试未验证 frontend 真理？
□ db_api 路径来自 targetFiles？ 列名逐字一致？ boundary(NOT NULL/PK/ENUM)+事务检查覆盖？
```

全部通过但测试仍失败 → fix_target=source → 加载 D

---

## 真理产出（测试通过时）

🛑 当 B 判断 `total>0 && failed==0` 时，测试全部通过，本层验证完成。此时 **B 产出真理** 供上层使用。

真理格式见 `skill/test/truths/{layer}.md`。各层产出不同的 key：

| 层 | 产出 key | 见 |
|----|---------|-----|
| auth | `token_config` | truths/auth.md |
| api | `routes` | truths/api.md |
| db_api | `sql_columns_verified` | truths/db_api.md |
| navigation | `jumps` | truths/navigation.md |
| backend_proc | `services` | truths/backend_proc.md |
| logic | `flows` | truths/logic.md |
| scenario | `chains` | truths/scenario.md |

🛑 真理通过 `<!--FINAL-->` JSON 输出，调度器自动存储。同层和上层通过 dependencies 获取。

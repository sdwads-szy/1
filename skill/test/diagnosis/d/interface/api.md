# D: api — 源代码诊断 + 修复验证

🛑 通用规则见 [../interface.md](../interface.md)。

## 角色

D 是 api 层**源代码分析专家**。B 在确认测试代码正确后加载 D 来写 source ban。C 修复源码后 D 执行验证。

## 职责一：源代码根因分析（供 B 加载）

B 确认测试干净后加载 D，D 提供以下知识帮助 B 写精准的 source ban。

### 源码断点定位

api 层用 fs.readFileSync 验证契约——失败意味着**源码结构与前端调用不匹配**：

| 测试症状 | 源码根因 | 断点位置 |
|---------|---------|---------|
| toContain(path) 失败 | routes 文件中缺对应路由行 | routes/{file}.js |
| toContain(field) 失败 | controller 中 `req.body` 解构缺字段 | controller 函数前几行 |
| toContain('authenticate') 失败 | 路由定义中第二个参数不是 authenticate | router.{method}() 参数列表 |
| toContain('hasRole') 失败 | admin 路由中无 hasRole 调用 | router.{method}() 参数列表 |
| response 格式不符合 | controller 未使用 response.success(res, data) 模式 | return/res.json 行 |
| 错误码映射不存在 | controller 的 catch 块缺 errorMap | controller 的 catch 块 |

### C 常见改错方式（B 用来写 ⚠️C注意）

| C 错误 | 为什么错 | ⚠️预警 |
|--------|---------|--------|
| 加路由但 method 写错 | 前端用 POST 但路由写了 GET | 对齐前端 API 真理中的 method |
| 加路由但 path 多/少前缀 | 路由 `/create` vs 前端 `/api/orders` | 对齐前端真理中的完整 path |
| 加 authenticate 放错位置 | 放到了 handler 后面 | 第二个参数必须是 authenticate |
| 补 req.body 字段拼写错 | `req.body.phoneNumber` 非真理中的 `phone` | 对齐前端真理中的字段名 |
| 改 response 缺 data 包装 | `res.json(orderId)` 非 `{success,data}` | 统一 `{success, data, message}` |

### 防作弊底线

```
□ app.use(authenticate) 被注释/删除 → CHEAT
□ hasRole 被删除或参数为空 → CHEAT
□ res.status() 全部硬编码 200 → CHEAT
□ 输入校验全部删除 → CHEAT
□ 字段全部删除只留空对象 → CHEAT
□ 修改了测试文件 → CHEAT(fix_target=test)
```

---

## 职责二：验证 C 的修复

C 修改源码后重跑测试。D 执行验证。

### 输入

| 输入 | 含义 |
|------|------|
| `raw_result` | C 修改后重跑的 Jest JSON——fs.readFileSync 断言结果 |
| `source_contents` | C 修改后的源码（routes/controller） |
| `B原始ban` | B 产出的 ban 列表（指出哪些路由/字段/中间件不匹配） |

### 分类判定

**failed=0 → 通过。**

**failed>0 → 对照 B 原始 ban 逐条分类：**

| 分类 | 含义 | 特征 |
|------|------|------|
| UNCHANGED | B 的 ban 再次命中 | C 没改或改错文件/行号 |
| REGRESSION | B时PASS → D时FAIL | C 改坏了原本匹配的断言 |
| DEGRADED | B 的 ban 列表中不存在的新失败 | C 引入了新问题 |
| CHEAT | C 删约束/中间件/校验来通过 | 见防作弊底线 |

### 验证步骤

**1. 变更分析** — C 改了哪些文件/行？改动是否在 B ban 指向的位置？

```
📝 C 变更:
  ✓ B ban#1 (routes/order.js:5) → C 添加了 router.post ✅
  ✗ B ban#2 (app.js:23) → C 未修改 ❌
  ⚡ 额外改动: middleware/auth.js:10 ⚠️
```

**2. 逐条验收** — 每条 B ban 对应测试结果。🛑 逐 category 验证：correct 通过 ≠ error/auth/boundary 通过。

**3. 回归扫描** — 找出 "B时PASS → D时FAIL" 的用例。

| 高频 REGRESSION | C 的典型错误 |
|---------------|------------|
| 添加路由但误删其他路由 | toContain 断言从 PASS 变 FAIL |
| 改 controller 字段解构 | 其他测试的字段名断言失败 |
| 改了共享中间件导入 | 所有路由的 authenticate 断言失败 |
| 改了 response 调用模式 | response.success 格式断言从 PASS 变 FAIL |

**4. 意图分析** — DEGRADED vs CHEAT。三要素：动机（能让测试通过吗）+ 影响（破坏什么）+ 替代（有正确方式吗）。

**5. 二次指导** — 告诉 C 下一步怎么修：

| 分类 | 二次指导 |
|------|---------|
| UNCHANGED | C 改了什么 vs B 要求改什么 + 正确文件:行号 + 正确代码 |
| REGRESSION | 哪个改动导致 + 如何在保持修复的同时限定影响范围 |
| DEGRADED | 新错误根因 + 对照契约给出正确字段/校验/类型 |
| CHEAT | 作弊行为 + 要求回滚 + 正确实现 + ⚠️ 警告 |

### D Ban 格式

```
f=api|source|{file}:{行号}|{分类}
b=DON'T: {C做了什么}导致{什么测试失败} — {深层原因}
| C改动: {C的代码变更}
| B要求: {B原始ban的fix}
| fix: {第二次修复的完整代码}
| ⚠️ C注意: {风险预警}
| target=source
```

示例：

```
f=api|source|routes/order.js:6|REGRESSION
b=DON'T: C 在 routes/order.js:6 添加了 router.post('/orders', orderController.create)，
但漏了 authenticate 中间件。导致原本 PASS 的中间件链断言现在 FAIL。
| C改动: router.post('/orders', orderController.create) — 缺第二个参数 authenticate
| B要求: 添加 router.post('/orders', authenticate, orderController.create)
| fix: routes/order.js:6 改为:
  router.post('/orders', authenticate, orderController.create);
| ⚠️ C注意: 添加 authenticate 后确认公开接口路由不受影响。
  authenticate 必须作为第二个参数（在 handler 之前）。
| target=source
```

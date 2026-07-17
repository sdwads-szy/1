# B: nfr — 测试代码诊断

🛑 通用规则见 [../logic.md](../logic.md)。

## 角色

B 评估 nfr 层**测试代码**写对了没有。nfr 是质量层，安全测试用 jest+supertest 发送攻击载荷，性能测试用 k6/autocannon。

🛑 nfr 的核心认知：**攻击载荷被拦截 = 正确行为（correct），不是 error。**

## 🛑 真理使用

nfr 的 prompt 中 `## 🛑 下层真理` 按 NFR 类型不同：
- **端点型**（性能/并发/SQL注入/限流/可用性）→ `@truth t_scenario_*` → `chains[].endpoints[]`（method/path/request_fields/auth_required）
- **页面型**（XSS）→ `@truth t_scenario_*` → `chains[].pages[]` + `@truth t_nav_*` → `jumps[]`
- **配置型**（HTTPS/CORS）→ `@truth t_infra_app` → 中间件/服务器配置
- **Token 安全** → `@truth t_auth_token` → token_config（secret/expiresIn/injection）
- `@truth t_api_*` → routes（端点列表）→ 性能测试
- `@truth t_backendproc_*` → services（函数签名）→ 限流测试

测试通过时产出真理，格式见 `skill/test/truths/nfr.md`。

- 测试代码有 bug → `fix_target=test`
- 测试代码干净但测试失败 → `fix_target=source` → 加载 D

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `test_file` | 审查对象——攻击载荷 + supertest 请求 + 断言 |
| `testScenarios` | 对照标准——input(攻击载荷)/output(期望行为，如拦截) |
| `raw_result` | Jest JSON |

## 逐项检查

### 1. 攻击载荷强度

🛑 payload 必须覆盖标准攻击向量，不能只用最基础的。

| 测试类型 | 应有载荷 | 常见错误 | 子类型 |
|---------|---------|---------|--------|
| SQL 注入 | `'; DROP TABLE--`、`UNION SELECT`、盲注 `' AND 1=1--` | 只用 `' OR 1=1` | WEAK_PAYLOAD |
| XSS | `<script>alert(1)</script>`、`<img onerror=alert(1)>`、`<svg onload=alert(1)>` | 只用一个标签 | WEAK_PAYLOAD |
| CORS | 非白名单 Origin、无 Origin、子域名伪造 | 只测了一个 Origin | WEAK_PAYLOAD |
| Token 篡改 | 错误 secret、伪造 payload、过期 token | 只测了无 token | WEAK_PAYLOAD |

### 2. 期望值正确性

🛑 nfr 的 correct = **攻击被安全拦截**。安全拦截返回 200/400 都是正确的，唯独不能返回 500。

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 期望拦截而非崩溃 | 期望 `res.status === 500`（把安全测试当 error 测） | WRONG_EXPECT |
| 期望拦截而非放行 | 期望 `res.status === 200` 且返回正常数据（没拦截） | WRONG_EXPECT |
| 不要求精确状态码 | 拦截可以返回 200/400/403，核心断言是 `not.toBe(500)` | WRONG_EXPECT |

### 3. 并发测试正确性

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 使用 Promise.all 真并发 | `for...of await` 实际串行——不会触发竞态 | SEQUENTIAL_CONCURRENT |
| 并发数合理 | jest 只能测 2 并发（`Promise.all([order(), order()])`）；真实压测用 k6 | WRONG_TEST_DATA |
| 期望有失败 | 2 并发同 SKU → `expect(success).toBe(1); expect(fail).toBe(1)` | WRONG_EXPECT |

### 4. RateLimit 测试

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 请求量超过阈值 | 只发 5 个请求期望 429——阈值通常 20-100+ | WRONG_TEST_DATA |
| 使用 Promise.all 并发 | 顺序 await 不算并发请求 | SEQUENTIAL_CONCURRENT |
| 期望有 429 | `responses.some(r => r.status === 429)` 而非要求全部 429 | WRONG_EXPECT |

### 5. 场景覆盖

| 场景 | 内容 |
|------|------|
| SQL 注入 | 搜索/登录等入口 → 参数化拦截 |
| XSS | 输入/输出处 → 转义 |
| CORS | 非白名单 Origin → 拒绝 |
| Token 篡改 | 伪造/过期/错 secret → 401 |
| RateLimit | 超频 → 429 |
| 并发超卖 | 同 SKU 并发 → 1 成功 1 失败 |

→ 子类型: MISSING_CATEGORY

---

## 判定

### total=0 → fix_target=test

```
SyntaxError        → test_file:行号 | SYNTAX
MODULE_NOT_FOUND   → test_file:行号 | MISSING_MODULE
```

### total>0 && failed>0

**先查上面 5 项。** 查到 → fix_target=test。全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

```
f=nfr|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```

示例：

```
f=nfr|test|test/nfr_rate.test.js:20|WRONG_TEST_DATA
b=DON'T: testScenario "RateLimit限流" 期望超频返回 429。
测试只发了 5 个请求就断言 429。限流中间件默认 max=20-100，
5 个请求远未达到阈值，测试永远不会触发 429。
| fix: test/nfr_rate.test.js:20 改为:
  const requests = Array.from({length: 150}, () =>
    request(app).get('/api/products?keyword=test')
  );
  const responses = await Promise.all(requests);
  expect(responses.some(r => r.status === 429)).toBe(true);
| target=test
```

```
f=nfr|test|test/nfr_sql.test.js:12|WEAK_PAYLOAD
b=DON'T: testScenario "SQL注入防护" payload 只用 `' OR 1=1--`，
太基础。缺少标准注入向量：堆叠查询(`'; DROP TABLE--`)、
UNION 注入、盲注(`' AND SLEEP(5)--`)。
| fix: test/nfr_sql.test.js:12 补充 payload:
  it("堆叠查询被拦截", async () => {
    const res = await request(app).get("/api/search?keyword='; DROP TABLE users; --");
    expect([200,400]).toContain(res.status);
    expect(res.status).not.toBe(500);
  });
| target=test
```

```
f=nfr|test|test/nfr_concurrent.test.js:15|SEQUENTIAL_CONCURRENT
b=DON'T: testScenario "并发超卖" 期望同时下单触发竞态。
测试用 `for (const item of items) { await request(...) }` 顺序执行，
实际是串行——不会触发并发竞态条件，测试结果不可信。
| fix: test/nfr_concurrent.test.js:15 改为:
  const orders = items.map(item =>
    request(app).post('/api/order').send(item).set('Authorization', `Bearer ${token}`)
  );
  const responses = await Promise.all(orders);
  expect(responses.filter(r => r.status === 409).length).toBeGreaterThan(0);
| target=test
```

---

## 🛑 最终响应（JSON 必须用 `<!--FINAL-->` 包裹）

**B 只输出 ban——测试代码有问题时：**
```
<!--FINAL-->
[
  {"f": "nfr|test|{file}:{行号}|{子类型}", "b": "DON'T: {问题} — {为什么} | fix: {文件}:{行号} {完整修正代码} | target=test"}
]
<!--FINAL-->
```
🛑 每条 ban 必须含文件:行号 + 完整修正代码（L3 以上）。
🛑 同根因合并：多个 it() 同一问题 → 合并为 1 条 ban。
🛑 输出后立即停止，不要再调工具。

## 自检清单

```
□ 载荷: SQL注入覆盖堆叠/UNION/盲注？XSS覆盖script/img/svg？
□ 期望: 攻击被拦截=correct(200/400)？不期望500？
□ 并发: 用 Promise.all 真并发？并发数合理？期望至少1个失败？
□ RateLimit: 请求量超过阈值？用 Promise.all？
□ 覆盖: SQL注入 + XSS + CORS + Token + RateLimit + 并发？
```

全部通过但测试仍失败 → fix_target=source → 加载 D

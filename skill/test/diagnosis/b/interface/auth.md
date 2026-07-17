# B: auth — 测试代码诊断

🛑 通用规则见 [../interface.md](../interface.md)。

## 角色

B 评估 auth 层**测试代码**写对了没有。auth 有 4 个子维度：token（纯JWT）、middleware（静态检查）、store（静态检查）、guard（静态检查）。

- 测试代码有 bug → `fix_target=test`
- 测试代码干净但测试失败 → `fix_target=source` → 加载 D

## 输入

| 输入 | B 怎么用 |
|------|---------|
| `test_file` | 审查对象——JWT 测试 + 静态检查代码 |
| `testScenarios` | 对照标准——input(操作描述)/output(期望) |
| `raw_result` | Jest JSON |

## 逐维度检查

---

### 维度1: token — 纯 JWT

🛑 **token 测试绝对禁止 `require('../../app')` 和 `supertest`。** 直接用 `jwt.sign()` + `jwt.verify()`。

对照 testScenarios 检查：

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 未使用 HTTP | 测试 require('../../app') 或 request(app) | USED_HTTP_IN_AUTH |
| jwt.sign payload 含 {userId, role} | 只写了 {userId} 缺 role | MISSING_PAYLOAD_IN_TEST |
| 三段式 token 验证 | 没验证 token.split('.').length === 3 | MISSING_TOKEN_FORMAT_CHECK |
| jwt.verify 解码验证 | 只调了 verify 没断言 decoded.userId/role | MISSING_DECODE_ASSERT |
| 过期 token 测试 | 用 setTimeout 等自然过期，而非 expiresIn:'0s' | WRONG_EXPIRY_TEST |
| 过期 token 被拒绝 | 缺 `expiresIn:'0s'` 测试 | MISSING_EXPIRY_CASE |
| 伪造 token 被拒绝 | 缺 `expect(() => jwt.verify('fake.token', secret)).toThrow()` | MISSING_TAMPER_CASE |
| 篡改 payload → 验签失败 | 缺篡改 payload 后验签失败的 it() | MISSING_TAMPER_CASE |
| refresh token 含 type | jwt.sign 缺 `{type:'refresh'}` 字段 | MISSING_REFRESH_TYPE |
| refresh_token 当 access_token 用 → 被拒 | 缺这个边界测试 | MISSING_REFRESH_CROSS_USE |
| payload 空对象 → verify 通过但 userId undefined | 缺 boundary it() | MISSING_EMPTY_PAYLOAD |
| JWT_SECRET 一致 | 测试用的 secret 与源码不一致 | SECRET_MISMATCH_IN_TEST |

---

### 维度2: middleware — 静态检查

🛑 **middleware 测试用 `fs.readFileSync` + `toMatch/toContain`，不调 HTTP。**

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| 使用 fs.readFileSync | 用了 request(app) 调 HTTP | HTTP_IN_STATIC_CHECK |
| authenticate 注入 req.userId | toMatch 正则写错（如 `req\.userId\s*=\s*`） | WRONG_STATIC_PATTERN |
| 无 token 返回 401 | 没检查 401 返回逻辑 | MISSING_401_CHECK |
| 导出 authenticate | 缺 `expect(src).toContain('module.exports')` | MISSING_EXPORT_CHECK |
| 文件路径正确 | fs.readFileSync 路径与项目实际不一致 | WRONG_SRC_PATH |

---

### 维度3: store — 静态检查

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| localStorage key 为 'auth_token' | 检查了错误的 key 名（如 'token'） | WRONG_STORAGE_KEY |
| Authorization header 为 `Bearer ${token}` | 检查了错误的格式（如 'JWT xxx'） | WRONG_HEADER_FORMAT |
| 文件路径正确 | fs.readFileSync 路径错 | WRONG_SRC_PATH |

---

### 维度4: guard — 静态检查

| 检查项 | 常见错误 | 子类型 |
|--------|---------|--------|
| router 含 requiresAuth | 缺守卫检查 | MISSING_GUARD_CHECK |
| router 含 requiresAdmin | admin 路由缺管理员守卫检查 | MISSING_ADMIN_GUARD_CHECK |
| 不验证 frontend 真理 | 断言了 .vue 存在或 router 注册完整性 | VERIFIED_TRUTH |

---

## 判定

### total=0 → fix_target=test

```
SyntaxError        → test_file:行号 | SYNTAX
MODULE_NOT_FOUND   → test_file:行号 | MISSING_MODULE
```

### total>0 && failed>0

**先查上面 4 个维度的常见错误。** 查到 → fix_target=test。全部通过 → fix_target=source → 加载 D。

---

## Ban 格式

```
f=auth|test|{test_file}:{行号}|{子类型}
b=DON'T: testScenario "{场景名}" {哪里错了} — {为什么}
| fix: {测试文件}:{行号} {完整修正代码}
| target=test
```

🛑 fix 中代码完整可执行，不含 `...` 或占位符。

示例：

```
f=auth|test|test/auth_token.test.js:5|USED_HTTP_IN_AUTH
b=DON'T: testScenario "jwt.sign产出三段式token" 测试第5行
require('../../app') 使用 supertest 发 HTTP。token 测试应纯 JWT。
| fix: test/auth_token.test.js:5 改为:
  const jwt = require('jsonwebtoken');
  const token = jwt.sign({userId:1, role:'buyer'}, JWT_SECRET, {expiresIn:'24h'});
  expect(token.split('.').length).toBe(3);
  const decoded = jwt.verify(token, JWT_SECRET);
  expect(decoded.userId).toBe(1);
| target=test
```

```
f=auth|test|test/auth_token.test.js:20|WRONG_EXPIRY_TEST
b=DON'T: testScenario "过期token被拒绝" 测试用 setTimeout 等 token 过期。
jwt.sign 24h 过期无法通过 setTimeout 模拟。
| fix: test/auth_token.test.js:20 改为:
  const expired = jwt.sign({userId:1, role:'buyer'}, JWT_SECRET, {expiresIn:'0s'});
  expect(() => jwt.verify(expired, JWT_SECRET)).toThrow();
| target=test
```

```
f=auth|test|test/auth_middleware.test.js:8|HTTP_IN_STATIC_CHECK
b=DON'T: testScenario "authenticate 注入 req.userId" 测试用了 supertest。
middleware 检查应 fs.readFileSync 静态分析。
| fix: test/auth_middleware.test.js:8 改为:
  const src = fs.readFileSync('middleware/auth.js', 'utf-8');
  expect(src).toMatch(/req\.userId\s*=\s*decoded\.userId/);
| target=test
```

---

## 自检清单

```
□ token 测试: 无 require('../../app')、无 supertest？
□ token payload: jwt.sign 含 {userId, role}？
□ 过期测试: 用 expiresIn:'0s' 而非 setTimeout？
□ 覆盖: 正常 + 过期 + 伪造 + 篡改 + 空payload + refresh误用 共 ≥6 个 it()？
□ refresh: 含 type='refresh' + cross_use 被拒？
□ boundary: payload 空对象 verify 通过但 userId undefined？
□ mw 检查: fs.readFileSync（非 HTTP）？ authenticate + optionalAuth 导出完整？
□ store 检查: key='auth_token' + header='Bearer'？
□ guard 检查: requiresAuth + requiresAdmin 存在？不验证 frontend 真理？
□ 文件路径: 与项目实际结构一致？
```

全部通过但测试仍失败 → fix_target=source → 加载 D

# A: auth — Token + 中间件 + 存储 + 守卫

🛑 **auth 层绝对禁止 supertest 和 require('../../app')** — 这是 api 层的工具，不是 auth 层的。
🛑 auth 只做两件事: (1) jwt.sign/jwt.verify 直调 (2) fs.readFileSync 静态检查。
🛑 如果 testScenarios 中出现了 HTTP 端点路径（如 POST /api/auth/refresh）→ 这不是 auth 层任务，应该被归到 api 层。遇到这种情况，忽略该 scenario 并输出警告。

继承 [interface.md](../interface.md) 通用规则。代码模板见 [templates/interface/auth.md](../../../templates/interface/auth.md)。

## 🛑 测试点（必须逐条覆盖）

按 `testScenarios[].category` 选择对应行，按 "A 产出" 列生成 it() 块：

| 维度 | category | scenario 来自 | A 产出 | 断言方式 |
|------|----------|:---:|--------|---------|
| **token** | correct | prompt 已有 | 1 个 it(): sign → verify 解出字段 | `expect(decoded.userId).toBe(1)` |
| | error | prompt 已有 | 1 个 it(): 过期/错secret/伪造 token | `expect(() => jwt.verify(...)).toThrow(TokenExpiredError)` |
| | error | **A 自动补** | 1 个 it(): `expiresIn:'0s'` 立即过期 | `toThrow(TokenExpiredError)` |
| | boundary | **A 自动补** | 1 个 it(): payload 空对象 `{}` | verify 通过但 `decoded.userId === undefined` |
| **mw** | correct | prompt 已有 | 1 个 it(): fs.readFileSync → `toContain('authenticate')`, `toContain('optionalAuth')` | 纯文本匹配 |
| | error | **A 自动补** | 1 个 it(): 验证中间件导出了 `authenticate` 并注入了 `req.userId` | `module.exports` 含函数名 |
| **store** | correct | prompt 已有 | 1 个 it(): fs.readFileSync → `toMatch(/key.*auth_token/)` | 正则匹配 |
| | error | **A 自动补** | 1 个 it(): 验证 token 存储 key 名正确 | `toContain('Bearer')` |
| **guard** | correct | prompt 已有 | 1 个 it(): fs.readFileSync → `toContain('requiresAuth')` | 纯文本匹配 |
| | error | **A 自动补** | 1 个 it(): 缺守卫 → 越权访问应被拦截 | `toContain('401')` 或 `toMatch(/requiresAuth\|requiresAdmin/)` |

🛑 **最少测试点**: 每个维度 ≥2 个 it()（correct + error 各 1）。总 it() 数 ≥8。
🛑 "A 自动补" → prompt 中没有对应 scenario，由 A 根据模板自行生成。

## 4 个子维度速查

| 维度 | 测试方式 | 关键函数/文件 |
|------|---------|-------------|
| token | `jwt.sign` + `jwt.verify` 直调 | `require('jsonwebtoken')` |
| mw | `fs.readFileSync` 静态检查 | `middleware/auth.js` |
| store | `fs.readFileSync` 静态检查 | `src/utils/request.js` 或 `src/stores/user.js` |
| guard | `fs.readFileSync` 静态检查 | 路由文件或 `middleware/permission.js` |

🛑 token 测试 **禁止 require('../../app') 和 supertest** — 纯 JWT 直调。
🛑 不要 mock JWT——用真实 secret 和真实 jwt 库。

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/interface/auth.md](../../../repair/a/interface/auth.md)。

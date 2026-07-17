# C: auth — Token+中间件+存储+守卫修复

继承 [interface.md](../interface.md) 通用规则。

## 修复策略（按 B 子类型）

### Token 维度

| 子类型 | 症状 | 修复 |
|--------|------|------|
| USED_HTTP_IN_AUTH | auth 测试用了 supertest | 不改源码——这是测试代码问题（fix_target=test） |
| MISSING_PAYLOAD | jwt.sign payload 缺 userId/role | `jwt.sign({userId, role}, secret, {expiresIn})` 补全字段 |
| REFRESH_TYPE | refresh token 缺 type 字段 | `jwt.sign({userId, type:'refresh'}, refreshSecret, {expiresIn:'30d'})` |
| WRONG_EXPIRY | 过期 token 未被拒绝 | jwt.verify 确保检查 exp，禁止设 `ignoreExpiration:true` |
| MISSING_TAMPER | 篡改 payload 验签未失败 | jwt.verify 必须验证签名完整性 |
| MISSING_EMPTY_PAYLOAD | payload 空对象→verify 通过但无 userId | jwt.sign 调用处校验必填字段 |
| MISSING_REFRESH_CROSS_USE | refresh token 当 access token 用通过 | jwt.verify 检查 token type 字段，type≠'access' 则拒绝 |
| SECRET_MISMATCH | 多处 JWT_SECRET 不一致 | 统一所有文件用同一个 JWT_SECRET（从 process.env 读） |

### Middleware 维度

| 子类型 | 症状 | 修复 |
|--------|------|------|
| MISSING_INJECTION | req.userId 为 undefined | `middleware/auth.js`: `req.userId = decoded.userId` |
| MISSING_401 | 无 token 不返回 401 | authenticate 函数: `if (!token) return res.status(401).json(...)` |
| MISSING_EXPORT | 未导出 authenticate | `module.exports = { authenticate, optionalAuth }` |
| HTTP_IN_STATIC_CHECK | 静态检查用了 HTTP | 不改源码——测试代码问题 |

### Store 维度

| 子类型 | 症状 | 修复 |
|--------|------|------|
| WRONG_STORAGE_KEY | token 存取失败 | `localStorage.setItem('auth_token', token)` / `localStorage.getItem('auth_token')` |
| WRONG_HEADER_FORMAT | 请求不带 Bearer | `Authorization: 'Bearer ' + token` |

### Guard 维度

| 子类型 | 症状 | 修复 |
|--------|------|------|
| MISSING_GUARD | 未登录可访问需认证页面 | `router.beforeEach` 中加 `requiresAuth` 检查 |
| MISSING_ADMIN_GUARD | 普通用户可访问管理页面 | 管理路由加 `meta: { requiresAdmin: true }` 或在 beforeEach 中检查 role |

## 反作弊底线

```
□ 不能设 jwt.verify ignoreExpiration:true → CHEAT
□ 不能把 hasRole 改为所有 role 通过 → CHEAT
□ 不能删 authenticate 中间件 → CHEAT
□ 不能删 jwt.verify 的签名检查 → CHEAT
```

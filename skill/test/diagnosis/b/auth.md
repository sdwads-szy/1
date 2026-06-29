# b: auth 层 — 测试代码诊断

## 检查链

### 1. Token 获取
- 硬编码 token → 不可靠 → `fix_target=test`
- 应从 `t_api_auth` 的 produces 注入

### 2. payload 断言
- `expect(res.body.data.token).toBeTruthy()` → 不验证内容 → `fix_target=test`
- 应 `jwt.verify(token)` 并验证 `{userId, role, iat, exp}`

### 3. 过期测试
- 等 token 自然过期 → 不可靠 → `fix_target=test`
- 应 `jwt.sign({...}, secret, {expiresIn: '0s'})` → 立即过期

### 4. 越权测试
- 所有测试用同一个 admin token → `fix_target=test`
- 应用 buyer token 访问 admin 端点期望 403

## 判定
以上全部干净，测试仍失败 → `fix_target=source`

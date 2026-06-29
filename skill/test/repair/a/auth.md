# a: auth 层 — 测试修复

## ban 解读
auth 层测试验证 Token/权限。ban 指向 token 获取/payload 断言/越权测试问题。

## 修复策略

### 硬编码 token
- 治：beforeAll 中从 `t_api_auth` 的 produces 获取

### payload 断言弱
- `expect(res.body.data.token).toBeTruthy()` → 用 `jwt.verify(token)` 解出 payload 验证 `{userId, role}`

### 过期测试不可靠
- 等自然过期 → `jwt.sign({...}, secret, {expiresIn: '0s'})` 立即过期

### 越权测试缺失
- 用非 admin token 调 `/admin/*` → 期望 403

## 工具选择（优先 edit_batch）
- 硬编码 token / 断言弱 / 过期测试 → `edit_batch` 精准修
- 结构性崩塌 → `create_file` 重写

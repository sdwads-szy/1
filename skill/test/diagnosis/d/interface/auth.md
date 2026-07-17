# D: auth — 源代码诊断 + 修复验证

🛑 通用规则见 [../interface.md](../interface.md)。

## 角色

D 是 auth 层**源代码分析专家**。B 在确认测试代码正确后加载 D 来写 source ban。C 修复源码后 D 执行验证。

## 职责一：源代码根因分析（供 B 加载）

B 确认测试干净后加载 D，D 提供以下知识。

### 源码断点定位

auth 层 4 个子维度的源码断点：

**token 维度：**

| 测试症状 | 源码根因 | 断点位置 |
|---------|---------|---------|
| jwt.verify 解不出 userId | jwt.sign({}) 缺 userId | jwt.sign 调用处 |
| jwt.verify 解不出 role | jwt.sign({userId}) 缺 role | jwt.sign 调用处 |
| 过期 token 未被拒绝 | jwt.verify 有 ignoreExpiration:true | jwt.verify 调用处 |
| 伪造/篡改 token 未被拒绝 | jwt.verify 没抛异常 | jwt.verify 调用处 |
| 错 secret 仍能验证 | 多处 JWT_SECRET 不一致 | 所有 jwt.sign/verify 调用处 |
| refresh token 缺 type | jwt.sign 缺 {type:'refresh'} | refresh token 生成处 |
| refresh_token 当 access_token 用通过 | verify 未检查 token type 字段 | jwt.verify 调用处 |
| payload 空对象→verify 通过但无 userId | jwt.sign 未校验必填字段 | jwt.sign 调用处 |

**middleware 维度：**

| 测试症状 | 源码根因 | 断点位置 |
|---------|---------|---------|
| req.userId 为 undefined | authenticate 缺 `req.userId = decoded.userId` | middleware/auth.js |
| 无 token 不返回 401 | authenticate 缺 401 返回逻辑 | middleware/auth.js |
| 路由无认证 | 未导出 authenticate 或未挂载 | module.exports 或 router 定义 |

**store/guard 维度：**

| 测试症状 | 源码根因 | 断点位置 |
|---------|---------|---------|
| token 存取失败 | localStorage key 名不对 | src/stores/user.js |
| 请求不带 Bearer | Authorization header 格式错 | src/utils/request.js |
| 未登录可访问需认证页面 | router 缺 requiresAuth | src/router/index.js |
| 普通用户可访问管理页面 | router 缺 requiresAdmin | src/router/index.js |

### C 常见改错方式（B 用来写 ⚠️C注意）

| C 错误 | 为什么错 | ⚠️预警 |
|--------|---------|--------|
| 改 JWT_SECRET | 新 secret 无法解密旧 token → REGRESSION | 统一使用 .env 中的值 |
| 加 ignoreExpiration:true | 绕过过期检查 → CHEAT | 永远不设此选项 |
| 删了 hasRole | 去掉权限检查 → CHEAT | hasRole 必须正确实现 |
| 补了 role 但 refresh 没同步 | 登录 token 有 role 但 refresh 换发的新 token 无 | 全局搜索 jwt.sign |
| hasRole 实现允许所有 role | 不检查 req.user.role 是否匹配 | `roles.includes(req.user.role)` |
| payload 字段名不一致 | 有的地方用 userId 有的用 user_id | 统一字段名 |

### 防作弊底线

```
□ 删除 hasRole 或改为所有 role 通过 → CHEAT
□ jwt.verify 设置 ignoreExpiration: true → CHEAT
□ 删除 authenticate 中间件 → CHEAT
□ 修改测试文件 → CHEAT(fix_target=test)
```

---

## 职责二：验证 C 的修复

### 分类判定

| 分类 | 含义 | auth 层特征 |
|------|------|-----------|
| UNCHANGED | 同 ban 再命中 | C 补了 hasRole 但挂错路由 / jwt.sign 仍缺字段 |
| REGRESSION | B时PASS→D时FAIL | 改 JWT_SECRET 导致旧 token 全失效 |
| DEGRADED | 新失败 | 修 sign 时误删了 refresh token 的 type 字段 |
| CHEAT | 删验证/中间件 | 删 hasRole / 设 ignoreExpiration |

### 验证步骤

**1. 变更分析** — C 改了哪些文件？

**2. 逐条验收** — 逐条 B ban 对照测试结果。

**3. 回归扫描** — auth 层高频 REGRESSION：

| 原因 | 检测方法 |
|------|---------|
| 改 JWT_SECRET | 检查所有文件的 JWT_SECRET 值是否一致 |
| 加 ignoreExpiration | 搜索 jwt.verify 调用的选项参数 |
| 改 hasRole 实现 | 检查 hasRole 函数体是否仍检查 req.user.role |
| payload 不同步 | 全局搜索 jwt.sign 确保所有调用点补全 |

**4. 意图分析** — 三要素：动机+影响+替代。

**5. 二次指导**：

| 分类 | 二次指导 |
|------|---------|
| UNCHANGED | 正确的路由注册代码 + jwt.sign 完整参数 |
| REGRESSION | 统一所有文件用同一个 secret + 确保与 .env 一致 |
| DEGRADED | 对照契约 tokenConfig 补全字段 |
| CHEAT | 要求回滚 + 正确实现 + ⚠️ 安全不可妥协 |

### D Ban 格式

```
f=auth|source|{file}:{行号}|{分类}
b=DON'T: {C做了什么}导致{什么测试失败}
| C改动: {C的代码变更}
| B要求: {B原始ban的fix}
| fix: {第二次修复的完整代码}
| ⚠️ C注意: {风险预警}
| target=source
```

示例：

```
f=auth|source|controllers/authController.js:22|REGRESSION
b=DON'T: C 在 loginController 改了 JWT_SECRET 为 'new-secret'，
导致所有用旧 secret 签发的 token jwt.verify 失败(TokenExpiredError)。
原本 PASS 的 token 验证测试全部 FAIL。
| C改动: JWT_SECRET 从 process.env.JWT_SECRET 改为 'new-secret'
| B要求: 统一 JWT_SECRET 来源
| fix: authController.js:22 改回:
  const token = jwt.sign({userId, role}, process.env.JWT_SECRET, {expiresIn:'24h'});
  确保所有文件(middleware/auth.js, controllers/*.js)统一使用 process.env.JWT_SECRET。
| ⚠️ C注意: 永远不要硬编码 secret。修改 secret 会使所有已签发 token 失效。
  如果确实需要改 secret，必须同步更新 .env 和所有引用处。
| target=source
```

# d: auth 层 — 源码验证

## 验证步骤
1. 跑测试 → 全过 → Token/权限正确 → 完成
2. 仍有失败 → 定位：sign 问题？verify 问题？中间件问题？
3. B 已验证测试正确 → 失败一定是 C 的修改不对

## C 常见错误
| 错误 | 检测方式 | ban 指向 |
|------|---------|---------|
| 改了 JWT_SECRET 但没同步所有文件 | sign 和 verify 用不同 secret | 统一 secret |
| 补了 hasRole 但挂错路由 | buyer 仍能访问 admin | 路由前补 hasRole('admin') |
| 改了 token payload 但测试期望旧字段 | payload 字段名变化 | 对齐 auth 契约 tokenConfig |
| 补了 owner 校验但代码位置错 | 校验在 DB 操作之后 | owner 校验移到操作前 |

## 反作弊
- C 删了 hasRole 中间件来"通过" → 权限全开 → `fix_target=source` + CHEAT
- C 把 hasRole 改为所有 role 都通过 → `fix_target=source` + CHEAT

## 判定矩阵

| 失败 | 源码问题 | 修复 |
|------|---------|------|
| Token 生成失败 | JWT_SECRET 未配置或 sign 参数错 | 对齐 auth 契约 |
| Token 验证失败 | verify 用的 secret 不一致 | 统一 JWT_SECRET |
| 过期时间不对 | accessTokenExpiry 配置错 | 对齐 tokenConfig |
| 权限拦截失败 | hasRole 中间件未挂载 | 路由前补 hasRole |
| 越权 | 未校验 owner | req.user.id === resource.userId |

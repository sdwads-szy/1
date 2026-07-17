# C: api — 接口源码修复

🛑 **api 层 C 步骤修复的是后端源码**（路由定义、controller、响应格式），不是测试代码。

继承 [interface.md](../interface.md) 通用规则。测试是真理，ban 来自 B/D 诊断。

## 修复策略（按 B 子类型）

🛑 **修复前先看 frontend 真理**：prompt 中 `@truth t_frontend_api_*` 包含前端实际调用的 path/method/fields。**前端是权威来源**——后端路由必须对齐前端。

| 子类型 | 症状 | 修复 |
|--------|------|------|
| ROUTE_NOT_FOUND | 前端调用 `POST /api/xxx` 但后端 routes 中无对应路由 | 在 routes 文件中添加 `router.post('/xxx', authenticate, handler)` |
| MISSING_FIELD | controller 中 `req.body` 缺字段解构 | 补全 `const { field } = req.body` |
| MISSING_RESPONSE | controller 未使用 response.success/fail 返回 | 改为 `response.success(res, data)` 格式 |
| MISSING_AUTH | 路由缺 authenticate 中间件 | `router.{method}(path, authenticate, handler)` |
| MISSING_PERMISSION | admin 路由缺 hasRole | `router.{method}(path, authenticate, hasRole('admin'), handler)` |
| WRONG_PATH | 路由路径与前端调用不一致 | 对齐前端真理中的 path |
| WRONG_METHOD | 路由 method 与前端调用不一致 | 改为前端真理中的 method |

## 防作弊底线

```
□ 不能删 app.use(authenticate) → CHEAT
□ 不能删 hasRole → CHEAT
□ 不能把所有 status 硬编码 200 → CHEAT
□ 不能删输入校验 → CHEAT
□ 不能改前端 src/api/*.js（那是 frontend 层的文件）→ CHEAT
```

# C repair: 接口层

D 判定分类后 C 的二次修复策略。适用于 api / auth / db_api / navigation。

## UNCHANGED — 同 ban 再命中

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| api | 改错路由文件/controller 函数 | 对照 B ban 的文件:行号确认改对位置 |
| api | middleware 挂载位置错 | authenticate 必须在 router.{method}() 第二个参数 |
| api | 🆕 `const authenticate = require('./middleware/auth')` 导致 app 启动崩溃 | 改为 `const { authenticate } = require('./middleware/auth')`（auth.js 导出的是对象 `{authenticate, optionalAuth}`，必须解构） |
| api | 🆕 改了 routes 后 app.js 启动不了 | `node -e \"require('./app')\"` 验证，不改其他文件的前提下确保加载链完整 |
| auth | jwt.sign 仍缺字段 | 确认 payload 含 {userId, role, type:'refresh'?} |
| auth | hasRole 挂错路由 | 确认是 `router.{method}(path, hasRole('admin'), handler)` |
| auth | 补了 payload 但 refresh token 没同步 | 全局搜索所有 jwt.sign 调用点 |
| db_api | 改错 DDL 文件 | 确认是 B ban 指向的表文件 |
| db_api | 加 NOT NULL 列无 DEFAULT | ALTER TABLE 加 DEFAULT 值 |
| db_api | 事务内 db.query() 仍没改 conn | 全部改为 conn.query() |
| navigation | 只改了 push 没改 route 定义 + 目标页读取 | 🛑 三端同时检查 |
| 🆕 api | correct 场景全部 40x — 种子数据缺失 | **不是 C 的责任**。确认 controller/service 逻辑正确后，ban 标注 `SEED_DATA_NEEDED`，由 integ 层补齐 |
| 🆕 api | 所有场景 404 — app.js 缺路由挂载 | **如果 app.js 不在白名单** → ban 标注 `ROUTE_NOT_MOUNTED`，需要 integ 层修复 |

## REGRESSION — 原来 PASS 现在 FAIL

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| api | 改共享中间件影响其他路由 | 加条件限定影响范围 |
| api | 改共用 controller 破坏分支逻辑 | 确认所有分支路径 |
| auth | 改 JWT_SECRET 导致旧 token 全失效 | 统一所有文件用同一个 secret |
| auth | 加 authenticate 后公开接口也 401 | 公开接口用 optionalAuth |
| db_api | 修 A 列误删 B 列 | 回看 diff，恢复被误删列 |
| db_api | 加 NOT NULL 导致现有 INSERT 失败 | 设 DEFAULT 或先填充再加约束 |
| navigation | 改 A 页面导致 B 页面路由失效 | 检查共享 router 配置 |

## DEGRADED — 新错误

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| api | 加校验但规则写反（> vs <） | 复核校验条件 |
| api | 补字段但类型错 | 对照契约确认类型 |
| auth | 加 payload 字段缺失 | 对照 auth 契约 tokenConfig |
| auth | refresh token type 字段忘加 | jwt.sign 补 `{type:'refresh'}` |
| db_api | 新加列 DEFAULT 表达式错 | 检查 DEFAULT 语法 |
| db_api | ENUM 取值拼写错 | 对照契约逐字检查 |
| navigation | 新路由 path 缺 :paramName | 补动态段 |

## CHEAT

| 层 | 常见作弊 | 纠正 |
|----|---------|------|
| api | 删 authenticate/hasRole | 恢复中间件 |
| api | 硬编码 status 200 | 按契约恢复 |
| api | 删输入校验 | 实现正确校验 |
| auth | 删 hasRole / jwt.verify 设 ignoreExpiration | 恢复 |
| db_api | 删 NOT NULL/FK/PK | 恢复约束 |
| db_api | 事务内 query 不改 conn | 改为 conn.query() |
| navigation | 删路由注册 / router.push 改 window.location | 恢复 |

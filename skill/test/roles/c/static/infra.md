# C: infra — 基础设施修复

继承 [static.md](../static.md) 通用规则。

## 🛑 工作流程

1. **先读 prompt 中的「任务检查点」**：每条 checkPoint 定义了基础设施必须满足的规范
   - `package.json: name/version/scripts 字段存在` → 核对 package.json
   - `config/db.js 导出: pool, query, beginTransaction, commit, rollback` → 核对导出名完整
   - `middleware/auth.js 导出: authenticate, optionalAuth` → 核对导出
2. **对照 checkPoints 逐条验证**，缺失/不匹配的用 edit_batch/create_files 修复

## 修复策略

```
env变量不一致 → 以 .env.example 为准，同步 .env/.env.development/.env.production
package.json字段缺 → 补 name/version/scripts/dependencies（🛑 禁止添加 "type": "module" — 会破坏后端 CJS 代码）
npm 依赖缺失 → src/ 下 import 的包不在 package.json 中，补到 dependencies 或 devDependencies，然后 npm install
jest配置错 → testMatch='test/**/*.test.js'，单层，无projects
config/db.js导出缺 → 补 pool/query/beginTransaction/commit/rollback/testConnection
config/logger.js导出缺 → 补 info/error/warn/debug
middleware/auth.js导出缺 → 补 authenticate/optionalAuth + req.userId注入
middleware/permission.js导出缺 → 补 hasRole
middleware/errorHandler.js导出缺 → 补 errorHandler
utils/response.js导出缺 → 补 success(res,data,msg)/fail(res,msg,code,data)
导出风格不统一 → module.exports.xxx 或 {xxx} 统一
```

## 反作弊

```
□ 不能把 db.js 的 pool 改 {} 空对象 → CHEAT
□ 不能删 response.js 的错误处理分支 → CHEAT
□ 不能把 .env 变量截断 → CHEAT
```

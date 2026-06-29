# 集成工程师 Agent Skill

## 角色
集成工程师。所有业务 agent 已完成。你的任务：闭合检查 + 路由注入 + 环境收尾。

## 🛑 上游真理

所有上游 agent 已完成。你必须对齐所有 `@truth` 块。

## 🛑 强制闭合检查（集成前逐项执行，顺序不可变）

### 检查 1：前端 API ↔ 后端路由匹配
- 读取 `src/api/*.js` 中每个 `request({ url: '...', method: '...' })` 的实际 URL 和 method
- 读取 `routes/*.js` 中每个 `router.{method}('...')` 的实际路径
- 🛑 前端调用的每个 API → 必须存在对应的后端 route（method + path 一致）
- 不一致则修正前端 API 路径

### 检查 2：前端路由注册 ↔ 页面文件存在
- 读取 `src/router/index.js` 中每个 `component: () => import('...')` 的实际路径
- 🛑 每个 import 路径 → 对应的 Vue 文件必须存在
- 不存在的 → 修正 import 路径或移除路由条目

### 检查 3：app.js require ↔ 文件存在
- 读取 `app.js` 中所有 `require('...')` 的相对路径
- 🛑 每个 require → 对应的 JS 文件必须存在
- 不存在的 → 移除或修正

### 检查 4：前端导出格式
- 所有 `src/api/*.js` 必须使用命名导出（`export function`），无 `export default`

### 检查 5：数据库表使用情况
- 列出 `database/*.sql` 中所有 CREATE TABLE 的表名
- 扫描 `services/*.js` 中的 FROM/JOIN/INSERT/UPDATE 目标表名
- 🛑 每个数据库表 → 至少被一个 service 引用（否则是死表）
- 每个 service 引用的表 → DDL 中存在（否则 SQL 会失败）

### 检查 6：package.json scripts ↔ 文件存在
- `package.json` 中每个 `"scripts"` 引用的 JS 文件必须存在
- 不存在的 → 移除 scripts 条目或创建文件

### 检查 7：env 变量 ↔ 代码引用
- 扫描所有 `.js`/`.vue` 文件中的 `process.env.X`，去重
- 确保 `.env.example` 包含所有引用的变量
- 代码引用但 .env.example 缺失的 → 补充

## 核心要求
1. 后端路由注入 `app.js` 的 `// ROUTES_INJECTION_POINT` 标记处。
2. 前端路由注入 `src/router/index.js` 的 `// IMPORT_INJECTION_POINT` 和 `// ROUTES_INJECTION_POINT` 标记处。
3. 确保 `src/main.js` 已导入并使用 router。
4. 路由表必须包含：根路径重定向 + 404 通配符（`/:pathMatch(.*)*`，始终在路由数组最后）。

## 环境收尾
- 遍历所有 `.js`/`.vue` 提取 `process.env.X`，去重
- 补齐 4 个 env 文件（.env / .env.example / .env.development / .env.production）的变量集一致性
- 维护 `scripts/init-db.js` 的 `SQL_FILES` 数组（FK 依赖序）
- 确保 `scripts/seed-users.js` 存在且可运行

## 禁止行为
- 不自行推断路由路径，一律使用闭合检查的实际结果
- 不修改 app.js / router/index.js 中除注入标记以外的内容
- 🛑 **不跳过任何闭合检查步骤**

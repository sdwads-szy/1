# c: db 层 — 源码修复

## 🛑 db 层源码 = database/*.sql（DDL 源头），scripts/init-db.js 只是加载器

**init-db.js 用 `loadSQL(filename)` 从 database/ 读 SQL 执行，不包含 DDL。**
修复分两步：先查 SQL 文件，再查加载器。

## 下层真理（不可质疑 — 来自 bans_text）
- **infra**: DB 连接可用 ← 不怀疑环境
- **同层 db**: 前置 db 任务的表结构正确 ← FK 目标表已确认

## 修复策略

### Table doesn't exist（最高频）
- 症状: `Table 'testdb.xxx' doesn't exist`
- 🛑 按顺序排查：
  1. `read_files()` 读 `database/` 下是否有该表的 `schema_*.sql` 文件
  2. SQL 文件存在 → 检查 `scripts/init-db.js` 的 `SQL_FILES` 数组是否包含它 → 缺 `edit_batch` 补
  3. SQL 文件存在 + SQL_FILES 有 → 检查 `module.exports` 是否有导出函数 → 缺 `edit_batch` 补一行
  4. SQL 文件不存在 → 需数据库设计师重新生成（C 不创建 SQL 文件）
  5. **禁止在 init-db.js 里写 CREATE TABLE**——DDL 属于 database/*.sql

### 字段类型/约束/索引与契约不一致
- 症状: DESCRIBE 结果与 testScenarios.then 不符
- 治: `read_files()` → 读对应的 `database/schema_*.sql` → `edit_batch` 改 DDL
- **不在 init-db.js 里改，在 SQL 文件里改**

### init-db.js 导出缺失
- 症状: `createXxxTable is not a function`
- 治: `edit_batch` 在 module.exports 加一行导出函数（`loadSQL` + `connection.query`）

### SQL_FILES 数组不完整
- 症状: 某表跑 `main()` 时未被创建
- 治: `edit_batch` 把文件名加入 SQL_FILES，FK 依赖序正确

## 工具选择
- 改 SQL 文件 → `edit_batch` 精准修
- 补 init-db.js 导出/数组项 → `edit_batch` 加一行
- 整个 SQL 文件缺失 → C 不创建，由数据库设计师处理

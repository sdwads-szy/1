# d: db 层 — 源码验证

## 验证步骤
1. 跑测试 → 全过 → DDL 与 model 契约一致 → 完成
2. 仍有失败 → 检查 C 是否改了正确的 SQL 文件
3. 对照失败的字段/约束名定位 DDL 中具体位置

## C 常见错误
| 错误 | 检测方式 | ban 指向 |
|------|---------|---------|
| SQL_FILES 数组缺文件 | 表未创建 | 把 SQL 文件名加入 SQL_FILES |
| module.exports 缺导出 | createXxxTable is not a function | 补导出函数 |
| 改了 database/*.sql 但没重跑 init-db.js | 表结构未变化 | 重新执行 init-db.js |
| FK 引用目标表不存在 | C 改了 FK 但目标表未创建 | 先确保父表存在 |
| 表名写错 | Table not found | 对照 SQL 文件和契约 |

## 反作弊
- C 删了约束/索引来"通过" → `fix_target=source` + CHEAT
- C 把所有字段改为 TEXT 类型 → `fix_target=source` + CHEAT
- C 在 init-db.js 里写 CREATE TABLE 代替 SQL 文件 → `fix_target=source` + CHEAT

## 判定矩阵

| 失败 | 源码问题 | 修复 |
|------|---------|------|
| Table doesn't exist | SQL_FILES 缺文件 或 init-db.js 未执行 | 补数组项或重跑脚本 |
| 字段类型错 | database/*.sql 的 DDL 与契约不一致 | ALTER TABLE 或改 SQL 文件 |
| UNIQUE 缺失 | SQL 文件缺 UNIQUE INDEX | 按契约补 |
| FK 缺失 | SQL 文件缺 FOREIGN KEY | 按契约补 |
| INDEX 缺失 | SQL 文件缺索引 | 按契约 indexes 补 |
| ENUM 取值不符 | SQL 文件 ENUM 值与契约不一致 | ALTER TABLE 或改 SQL 文件 |

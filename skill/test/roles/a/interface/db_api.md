# A: db_api — 数据库列名验证

继承 [interface.md](../interface.md) 通用规则。代码模板见 [templates/interface/db_api.md](../../../templates/interface/db_api.md)。

## 工作流

场景定方向，**模板定参数提取方式**。

🛑 参数提取规则全部在模板中。这里不重复。

1. 读场景 → 确定测试范围
2. 按模板提取参数（表名、列名、NOT NULL 列、PK 列、service 文件路径）→ 填入骨架
3. create_files 输出

## 独有规则

- 🛑 **连接真实数据库验证**：用 `mysql2.createConnection` + `SHOW COLUMNS FROM table`，不解析 DDL 文本
- 🛑 **不用正则匹配 DDL**：DDL 文本格式不可控（反引号、空格、注释），`SHOW COLUMNS` 返回结构化数据，用 `toBe('NO')` / `toBe('PRI')` 断言
- DB 连接参数从 `process.env` 读取（`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`），`require('dotenv').config()` 加载
- 列名、表名从真理 JSON 提取，禁止编造
- 只验证列名存在性和约束（NOT NULL/PK/AUTO_INCREMENT），不验证 FOREIGN KEY（静态层已验证）
- Service SQL 列对齐：仍然 `fs.readFileSync` 读源码验证 INSERT 列数一致
- 🛑 测试文件路径: `test/{task_id}.test.js`

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/interface/db_api.md](../../../repair/a/interface/db_api.md)。

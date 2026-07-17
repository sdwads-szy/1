# C: db_api — DDL/SQL 修复

继承 [interface.md](../interface.md) 通用规则。db_api 验证数据库列名与契约一致 + service SQL 列对齐。

## 修复策略（按 B 子类型）

| 子类型 | 症状 | 修复 |
|--------|------|------|
| COLUMN_SPELLING_ERR | SHOW COLUMNS 中列名不存在 | DDL 中补该列定义，或修正 SQL 中拼写错的列名 |
| TABLE_NAME_ERR | SHOW COLUMNS 表名不存在 | 确认 DDL 中表名，修正 service 中的表名引用 |
| MISSING_COLUMN | DDL 缺列定义 | `ALTER TABLE ADD COLUMN` 或 CREATE TABLE 中补列 |
| TYPE_MISMATCH | 列类型与 SQL 用法不一致 | 对齐 DDL 列类型（VARCHAR↔INT↔DECIMAL） |
| MISSING_NOT_NULL | NOT NULL 约束缺失 | DDL 列定义加 `NOT NULL` |
| MISSING_PK | PRIMARY KEY 缺失 | 表定义尾部加 `PRIMARY KEY (id)` |
| AUTO_INCREMENT_NO_PK | AUTO_INCREMENT 列无 PRIMARY KEY | 该列同时设为 PRIMARY KEY |
| ENUM_MISMATCH | ENUM 取值与契约不一致 | 对齐 ENUM 定义值 |
| COLUMN_COUNT | INSERT 列数 ≠ VALUES 数 | Service SQL: 列列表和 VALUES 占位符数一致 |
| TX_CONN_MISUSE | 事务内用 db.query() 而非 conn.query() | 事务块内全部改为 `conn.query()` |
| DB_CONNECTION | 数据库连接失败 | 检查 .env 配置 + 运行 init-db.js |
| VERIFIED_TRUTH | 验证了不该验证的内容 | 不改源码——测试代码问题（fix_target=test） |

## 反作弊底线

```
□ 不能删 NOT NULL → CHEAT
□ 不能删 FOREIGN KEY → CHEAT
□ 不能删 PRIMARY KEY → CHEAT
□ 不能所有列改 TEXT → CHEAT
□ 不能事务内不改 conn.query() → CHEAT
```

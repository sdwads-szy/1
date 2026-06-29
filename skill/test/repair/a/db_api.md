# db-api层修复策略 (A步骤)
- 修复范围: Service SQL 列名、事务连接使用
- 列名不匹配 → 对照 DDL 修正 SQL 列名
- 事务内 db.query() → 改为 conn.execute()
- INSERT 列列表与 VALUES 数量不一致 → 对齐

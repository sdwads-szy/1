# d: db_api 层 — 源码验证

C 修改了 Service 文件中的 SQL 语句后，验证修复是否有效。

## 验证步骤

1. **SQL 列名验证**
   - 提取修改后 SQL 中所有 INSERT/SELECT/UPDATE 的列名
   - 逐列对照 DDL truth 中的合法列名
   - 仍有不存在的列名 → C 没改对 → ban 标记 COLUMN_MISMATCH

2. **INSERT 列数验证**
   - INSERT 的列列表数量 = VALUES 占位符数量？
   - 不匹配 → ban 标记 COLUMN_COUNT

3. **事务连接验证**
   - 事务体内是否还有 `db.query()`？
   - 有 → C 没改干净 → ban 标记 TX_CONN_MISUSE

4. **操作类型匹配**
   - db_api truth 声明 CRUD_CREATE → Service 中是 INSERT？
   - db_api truth 声明 CRUD_READ → Service 中是 SELECT？
   - 不匹配 → ban 标记 OP_MISMATCH

## ban 指纹格式

f = db_api|source|{service文件}|{子类型}

子类型: COLUMN_MISMATCH / COLUMN_COUNT / TX_CONN_MISUSE / OP_MISMATCH

# db_api 真理提取

本层产出 SQL 列名验证结果 + **实现细节**（通过 SHOW COLUMNS 查真实数据库 + 读源码获得）。

**上层**: api（字段对齐）、backend_proc（service 查询了哪些 DB 列 + 查询模式细节，用于写 mock）。
**同层**: 表验证链——t_dbapi_auth 产出 users 表的列验证，其余 db_api 任务通过 dependencies 信任该表已验证。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "sql_columns_verified": [
      {
        "service_file": "services/authService.js",
        "function": "findUserByPhone",
        "table": "users",
        "operation": "SELECT",
        "columns": ["id", "phone", "password_hash", "nickname", "avatar", "role", "status"],
        "query_order": 1,
        "sql_params": ["phone"],
        "sql_features": [],
        "connection": "pool"
      },
      {
        "service_file": "services/authService.js",
        "function": "registerUser",
        "table": "users",
        "operation": "INSERT",
        "columns": ["phone", "password_hash", "role", "status", "created_at"],
        "query_order": 2,
        "sql_params": ["phone", "hash", "role", "status"],
        "sql_features": [],
        "connection": "transaction"
      }
    ]
  },
  "exposed_to_peers": {
    "verified_tables": ["users", "login_logs"]
  }
}
```

🛑 一个 service 文件可能操作多个表——每个 function+table 组合都要在 `sql_columns_verified[]` 中列出一条。
🛑 `query_order` 按源码中 `db.query()`/`conn.query()` 出现顺序编号，从 1 开始。这是 backend_proc 测试 `mockResolvedValueOnce` 链的顺序依据。

### exposed_to_upper

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `service_file` | string | backend_proc | Service 文件路径 |
| `function` | string | backend_proc | Service 函数名 |
| `table` | string | backend_proc | 操作的数据库表名 |
| `operation` | string | backend_proc | SELECT/INSERT/UPDATE/DELETE |
| `columns` | string[] | api, backend_proc | 🛑 SQL 列名。已通过 SHOW COLUMNS 在真实数据库中验证存在 |
| `query_order` | int | backend_proc | 🆕 本函数内第几次查询（1-based，`mockResolvedValueOnce` 链顺序） |
| `sql_params` | string[] | backend_proc | 🆕 SQL 的 `?` 占位符对应的参数名数组。空数组 = 无占位符（如 SQL 用 `CURDATE()` 内联）。`toHaveBeenNthCalledWith` 断言 param count = 本数组长度 + 1(sql) |
| `sql_features` | string[] | backend_proc | 🆕 SQL 特殊模式: `["JOIN"]` / `["CURDATE"]` / `["subquery"]` / `["ON DUPLICATE KEY"]` |
| `connection` | string | backend_proc | 🆕 连接模式: `"pool"`(db.query直连) / `"connection"`(db.getConnection池) / `"transaction"`(conn.query事务内)。决定 mock 方式 |

### exposed_to_peers（同层表验证链）

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `verified_tables` | string[] | 同层 db_api 任务 | 本任务已验证过的表名列表 |

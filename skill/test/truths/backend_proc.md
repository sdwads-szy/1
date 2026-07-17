# backend_proc 真理提取

本层产出已验证的服务函数签名 + **SQL 实现细节**。封装了 api + db_api 的全部验证结果，**作为 logic 层的唯一数据源**。

**上层**: logic（跨模块组合，只需要 backend_proc 真理）、scenario（全链路）、nfr（限流测试）。
**同层**: 业务流程链——t_bp_login 产出用户会话，t_bp_create_order 通过 dependencies 信任登录已验证。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "services": [{
      "file": "services/authService.js",
      "functions": [
        {
          "name": "sendSmsCode",
          "params": ["phone:string"],
          "returns": "{success:boolean, mockCode?:string}",
          "throws": ["INVALID_PHONE", "SMS_RATE_LIMIT", "SMS_SEND_FAILED"],
          "redis_ops": [
            {"op": "incr", "key": "sms:rate:{phone}", "ttl": 300, "note": "频率计数器"},
            {"op": "set", "key": "sms:{phone}", "ttl": 60, "note": "验证码缓存"}
          ],
          "env_dependent": {
            "SMS_MODE": "mock|real",
            "mock_behavior": "固定返回 '123456'",
            "real_behavior": "crypto.randomInt(100000, 999999)"
          },
          "sql_queries": [
            {
              "query_order": 1,
              "table": "users",
              "operation": "SELECT",
              "columns": ["id", "phone", "password_hash", "role", "status"],
              "sql_params": ["phone"],
              "sql_features": [],
              "connection": "pool"
            }
          ]
        },
        {
          "name": "registerUser",
          "params": ["phone:string", "smsCode:string", "password:string", "ip?:string", "device?:string"],
          "returns": "{userId:number, token:string, refreshToken:string, role:'buyer'}",
          "throws": ["INVALID_PHONE", "INVALID_PASSWORD_FORMAT", "SMS_CODE_INVALID", "PHONE_REGISTERED", "REGISTER_FAILED"],
          "transaction": true,
          "db_tables": ["users", "login_logs"],
          "sql_queries": [
            {
              "query_order": 1,
              "table": "users",
              "operation": "SELECT",
              "columns": ["id", "phone"],
              "sql_params": ["phone"],
              "sql_features": [],
              "connection": "pool"
            },
            {
              "query_order": 2,
              "table": "users",
              "operation": "INSERT",
              "columns": ["phone", "password_hash", "role", "status", "created_at"],
              "sql_params": ["phone", "hash", "user", "active"],
              "sql_features": [],
              "connection": "transaction"
            },
            {
              "query_order": 3,
              "table": "login_logs",
              "operation": "INSERT",
              "columns": ["user_id", "ip", "device", "created_at"],
              "sql_params": ["userId", "ip", "device"],
              "sql_features": [],
              "connection": "transaction"
            }
          ]
        }
      ]
    }]
  },
  "exposed_to_peers": {
    "session_verified": true
  }
}
```

🛑 一个 service 文件含多个函数——每个都要在 `functions[]` 中列出。每个函数的 SQL 查询都要在 `sql_queries[]` 中列出。logic 只需要依赖 backend_proc，不再依赖 api/db_api。

### exposed_to_upper（logic 的唯一数据源）

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | string | Service 文件路径 |
| `functions[].name` | string | 函数名 |
| `functions[].params` | string[] | 参数列表。格式 `"name:type"`，可选参数标 `?` |
| `functions[].returns` | string | 返回值结构（🛑 展开到叶子字段，如 `{userId:number, token:string, refreshToken:string}`） |
| `functions[].throws` | string[] | 可能抛出的 Error.message 列表（🛑 精确名，logic 断言用） |
| `functions[].transaction` | bool | 是否有 BEGIN→COMMIT/ROLLBACK 事务 |
| `functions[].db_tables` | string[] | 事务中操作的表名列表 |
| `functions[].redis_ops[]` | object | Redis 操作序列（op/key/ttl/condition） |
| `functions[].env_dependent` | object | 环境变量控制的行为差异（mock/real 模式） |
| **`functions[].sql_queries[]`** | object[] | 🆕 **SQL 实现细节（原 db_api 真理字段，封装到此）** |
| `sql_queries[].query_order` | int | 本函数内第几次查询（1-based，mockResolvedValueOnce 链顺序） |
| `sql_queries[].table` | string | 操作的表名 |
| `sql_queries[].operation` | string | SELECT/INSERT/UPDATE/DELETE |
| `sql_queries[].columns[]` | string[] | 🛑 SQL 列名，已通过真实数据库验证 |
| `sql_queries[].sql_params[]` | string[] | `?` 占位符参数名。空数组=无占位符（CURDATE 内联） |
| `sql_queries[].sql_features[]` | string[] | SQL 特殊模式: `["JOIN"]` / `["CURDATE"]` / `["ON DUPLICATE KEY"]` |
| `sql_queries[].connection` | string | `"pool"`(直连) / `"connection"`(连接池) / `"transaction"`(事务内) |

### exposed_to_peers（同层业务流程链）

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_verified` | bool | 用户登录/会话已验证，下游可直接假设 `req.userId` 有效 |
| `verified_functions` | string[] | 🆕 本任务已验证的 service 函数名列表。下游任务依赖此后，可信任这些函数已通过单元测试 |
| `verified_returns` | object | 🆕 已验证函数的返回值示例（`{"{fnName}": "{returns字段}"}`），下游可直接引用返回字段名 |

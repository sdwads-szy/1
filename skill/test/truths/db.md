# db 真理提取

本层产出 DDL 表定义。

**上层**: db_api（SQL列名验证）、frontend（v-model字段对齐 DB 列）。
**同层**: FK 链——子表任务需要父表的完整字段定义来验证外键引用。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "tables": [
      {
        "name": "users",
        "file": "database/schema/users.sql",
        "fields": [
          {"name": "id", "type": "INT", "nullable": false, "auto_increment": true},
          {"name": "phone", "type": "VARBINARY(128)", "nullable": false, "unique": true},
          {"name": "password_hash", "type": "VARCHAR(256)", "nullable": false},
          {"name": "role", "type": "ENUM('buyer','merchant','admin')", "nullable": false, "default": "buyer"},
          {"name": "status", "type": "ENUM('active','banned')", "nullable": false, "default": "active"},
          {"name": "created_at", "type": "TIMESTAMP", "nullable": false, "default": "CURRENT_TIMESTAMP"}
        ],
        "indexes": [{"name": "PRIMARY", "columns": ["id"]}, {"name": "idx_role_status", "columns": ["role", "status"]}],
        "foreignKeys": []
      },
      {
        "name": "login_logs",
        "file": "database/schema/users.sql",
        "fields": [
          {"name": "id", "type": "INT", "nullable": false, "auto_increment": true},
          {"name": "user_id", "type": "INT", "nullable": false},
          {"name": "ip", "type": "VARCHAR(45)", "nullable": false},
          {"name": "device", "type": "VARCHAR(255)", "nullable": true},
          {"name": "created_at", "type": "TIMESTAMP", "nullable": false, "default": "CURRENT_TIMESTAMP"}
        ],
        "indexes": [{"name": "PRIMARY", "columns": ["id"]}, {"name": "idx_login_logs_user", "columns": ["user_id"]}],
        "foreignKeys": [{"columns": ["user_id"], "refTable": "users", "refColumns": ["id"]}]
      }
    ],
    "seed": {
      "users": {
        "file": "database/seed/users.json",
        "rows": 3,
        "ids": [1, 2, 3],
        "test_users": [
          {"id": 1, "phone": "13800000001", "password": "123456", "role": "USER", "nickname": "测试买家张三"},
          {"id": 2, "phone": "13800000002", "password": "123456", "role": "USER", "nickname": "测试买家李四"},
          {"id": 3, "phone": "13800000003", "password": "123456", "role": "ADMIN", "nickname": "平台管理员"}
        ]
      }
    }
  },
  "exposed_to_peers": {
    "tables": "同 exposed_to_upper.tables。同层子表任务（如 t_db_order）通过 dependencies 获取父表结构来验证 FK"
  }
}
```

🛑 一个 SQL 文件可能含多个 CREATE TABLE——每个表都要在 `tables[]` 中列出一条。上面 users.sql 含 users + login_logs 两个表，全列出来了。
🛑 每个表**必须**有 `file` 字段——db_api 层需要这个路径来做 fs.readFileSync。禁止省略。
🛑 **seed 字段**：每张有种子数据的表必须在 `exposed_to_upper.seed` 中声明其 seed 文件路径、行数、ID 列表和测试账号信息。下游 scenario/logic 测试从中获取测试用户登录凭据。

### exposed_to_upper

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `name` | string | db_api, frontend | 表名。`CREATE TABLE \`xxx\`` |
| `file` | string | db_api | DDL 文件路径 |
| `fields[].name` | string | db_api, frontend | 列名 |
| `fields[].type` | string | db_api | 列类型 |
| `fields[].nullable` | bool | db_api | NOT NULL→false |
| `indexes[].name` | string | db_api | 索引名 |
| `indexes[].columns` | string[] | db_api | 索引列 |
| `foreignKeys[].columns` | string[] | db_api | FK 列 |
| `foreignKeys[].refTable` | string | db_api | FK 父表 |
| `foreignKeys[].refColumns` | string[] | db_api | FK 父表列 |

### exposed_to_peers（同层 FK 链）

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `tables` | object[] | 同层子表任务 | 与 exposed_to_upper.tables 相同。t_db_order 通过 dependencies 依赖 t_db_user，调度器将 t_db_user 的 tables 注入 t_db_order 的 prompt。子表任务用此验证 `FOREIGN KEY (user_id) REFERENCES users(id)` 的父表列真实存在 |

**同层传递路径**: `t_db_user` 产出 tables → `t_db_order` 在 dependencies 中声明依赖 → 调度器注入 t_db_user 的真理 → t_db_order 的 prompt 中看到父表结构。

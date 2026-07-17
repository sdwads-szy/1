# infra 真理提取

本层产出中间件/配置/工具函数的导出签名。

**上层（exposed_to_upper）**: auth（middleware 签名+注入）、peer_deps（导出名验证）、frontend（API client）。

**同层（exposed_to_peers）**: infra 内部 config→middleware→app 的配置链。同层任务验证自己文件的 require 时需要知道被引用文件的真实导出名。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "middleware": {
      "middleware/auth.js": {
        "exports": ["authenticate", "optionalAuth"],
        "injects": "req.user = {userId, role, iat, exp}"
      },
      "middleware/permission.js": {
        "exports": ["hasRole", "hasPermission", "hasAllPermissions"]
      }
    },
    "config": {
      "config/db.js": {"exports": ["pool", "query", "beginTransaction", "commit", "rollback", "testConnection"]}
    },
    "utils": {
      "utils/response.js": {"exports": ["success", "fail", "error", "unauthorized", "forbidden"]},
      "utils/encryption.js": {"exports": ["encrypt", "decrypt", "encryptPhone", "decryptPhone", "hashPassword", "comparePassword"]}
    }
  },
  "exposed_to_peers": {
    "config/db.js": {
      "exports": ["pool", "query", "beginTransaction", "commit", "rollback", "testConnection"],
      "used_by": ["middleware/auth.js", "middleware/errorHandler.js", "app.js"]
    },
    "utils/response.js": {
      "exports": ["success", "fail", "error", "unauthorized", "forbidden"],
      "used_by": ["middleware/auth.js", "middleware/permission.js", "middleware/errorHandler.js"]
    }
  }
}
```

### exposed_to_upper（上层）

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `middleware.{file}.exports` | string[] | auth | 该中间件文件的导出函数名。从 `module.exports = {xxx}` 提取 |
| `middleware.{file}.injects` | string | auth | JWT 验证后注入 req 的字段。auth 层写 JWT payload 的唯一依据 |
| `config.{file}.exports` | string[] | peer_deps | 配置文件的导出函数/对象名 |
| `utils.{file}.exports` | string[] | peer_deps | 工具文件的导出函数名 |

### exposed_to_peers（同层）

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `{file}.exports` | string[] | 同层 infra 任务 | 该文件的真实导出名。同层任务（如 t_infra_middleware）验证自己 `require('../config/db')` 时，需要知道 db.js 实际导出了什么 |
| `{file}.used_by` | string[] | 同层 infra 任务 | 引用该文件的同层文件列表。帮助下游判断"我依赖了哪些 infra 文件，它们的导出是否一致" |

**同层依赖由 test task 的 `dependencies` 声明**（如 t_infra_middleware 依赖 t_infra_config）。真理只提供验证数据。

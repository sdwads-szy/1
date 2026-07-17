# peer_deps 真理提取

本层产出同层模块间的 require/import 依赖验证结果。

**上层**: integ（最终集成验证）。
**同层**: peer_deps 任务之间——已验证的模块导出名供同层其他任务交叉引用。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {},
  "exposed_to_peers": {
    "verified_exports": {
      "config/db.js": {
        "exports": ["pool", "query", "beginTransaction", "commit", "rollback", "testConnection"],
        "verified_by": "t_peer_auth"
      },
      "utils/response.js": {
        "exports": ["success", "fail", "error"],
        "verified_by": "t_peer_auth"
      },
      "middleware/auth.js": {
        "exports": ["authenticate", "optionalAuth"],
        "verified_by": "t_peer_auth"
      }
    },
    "verified_requires": {
      "routes/auth.js": {
        "requires": [
          {"module": "../controllers/authController", "imports": ["register", "login"], "status": "matched"},
          {"module": "../middleware/auth", "imports": ["authenticate"], "status": "matched"}
        ],
        "verified_by": "t_peer_auth"
      }
    }
  }
}
```

### exposed_to_upper

空。peer_deps 的验证结果供 integ 收拢使用，但 integ 直接从 dependencies 获取全量。

### exposed_to_peers（同层交叉验证）

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `verified_exports.{file}.exports` | string[] | 同层 peer_deps 任务 | 该文件的真实导出名列表。同层其他任务验证 require 时对照此列表 |
| `verified_exports.{file}.verified_by` | string | 同层 | 哪个 peer_deps 任务验证的 |
| `verified_requires.{file}.requires[].module` | string | 同层 | require 的目标模块路径 |
| `verified_requires.{file}.requires[].imports` | string[] | 同层 | require 导入的名称。与 exports 对照验证 |
| `verified_requires.{file}.requires[].status` | string | 同层 | `"matched"`（导出导入一致）/ `"mismatched"`（不一致） |
| `verified_requires.{file}.verified_by` | string | 同层 | 哪个 peer_deps 任务验证的 |

**同层传递路径**: `t_peer_auth` 产出 verified_exports（config/db.js → exports=["pool","query"]）→ `t_peer_order` 依赖 t_peer_auth → 调度器注入同层真理 → t_peer_order 已知道 db.js 的真实导出，只验证 order 模块自己的 require 链。

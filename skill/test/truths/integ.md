# integ 真理提取

本层产出集成验证结果——路由挂载+环境完整性。消费所有静态层。

**上层**: 无（终端层）。
**同层**: integ 只有一个任务。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "routes_mounted": [{
      "file": "app.js",
      "routes": [
        {"path": "/api/auth", "router": "./routes/auth"},
        {"path": "/api/order", "router": "./routes/order"}
      ]
    }],
    "router_pages": [
      {"path": "/login", "component": "Login.vue"},
      {"path": "/home", "component": "Home.vue"}
    ],
    "env_complete": true,
    "missing_routes": [],
    "missing_env_vars": []
  },
  "exposed_to_peers": {}
}
```

### exposed_to_upper

| 字段 | 类型 | 说明 |
|------|------|------|
| `routes_mounted[].file` | string | 挂载文件（通常是 app.js） |
| `routes_mounted[].routes[].path` | string | 挂载的 URL 前缀 |
| `routes_mounted[].routes[].router` | string | 引用的路由文件 |
| `router_pages[].path` | string | 前端页面路由 path |
| `router_pages[].component` | string | 前端页面组件文件 |
| `env_complete` | bool | 环境变量是否完整 |
| `missing_routes` | string[] | 缺失的路由挂载 |
| `missing_env_vars` | string[] | 缺失的环境变量 |

### exposed_to_peers

空。integ 仅一个任务。

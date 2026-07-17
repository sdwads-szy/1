# frontend 真理提取

本层产出页面路径、路由定义、前端 API 调用。

**上层（exposed_to_upper）**: navigation（需要 router name + pages）、api（需要 api_calls 知道前端调了什么）。

**同层（exposed_to_peers）**: 前端模块之间的 API 模块引用。同层任务验证 `import {X} from '@/api/xxx'` 时，需要知道被引用模块的真实导出函数名。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "pages": [{"file": "src/pages/home/Home.vue", "route": "/"}],
    "router": [{"path": "/", "name": "Home", "component": "src/pages/frontend/home/Home.vue"}],
    "api_calls": [
      {"from": "src/api/auth.js", "endpoints": ["POST /auth/login", "POST /auth/register", "POST /auth/send-sms", "POST /auth/refresh"]},
      {"from": "src/api/category.js", "endpoints": ["GET /categories"]}
    ],
    "additional_api_calls_from_page": ["POST /auth/login (登录按钮)"]
  },
  "exposed_to_peers": {
    "api_modules": {
      "src/api/auth.js": {
        "exports": ["login(data)", "register(data)", "getMe()"],
        "imported_by": ["src/pages/frontend/auth/Login.vue", "src/pages/frontend/auth/Register.vue"]
      }
    },
    "stores": {
      "src/stores/user.js": {
        "state": ["token", "user"],
        "actions": ["setToken", "logout"],
        "getters": ["isLoggedIn"],
        "imported_by": ["src/pages/frontend/auth/Login.vue"]
      }
    }
  }
}
```

### exposed_to_upper（上层）

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `pages[].file` | string | navigation | 页面文件完整路径。从 targetFiles 取 .vue 文件 |
| `pages[].route` | string | navigation | 页面对应的 URL（参考用） |
| `router[].path` | string | navigation | 路由 path。从 `src/router/index.js` 提取 |
| `router[].name` | string | navigation | 🛑 路由 name。navigation 测试用 `toContain(routeName)` |
| `router[].component` | string | navigation | 路由对应的组件路径 |
| `api_calls[].from` | string | api | 前端 API 模块文件路径 |
| `api_calls[].endpoints` | string[] | api | 该模块调用的后端端点。格式 `"METHOD /path"` |
| `additional_api_calls_from_page` | string[] | api | 页面中额外调用的端点，格式 `"METHOD /path (说明)"` |

### exposed_to_peers（同层）

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `api_modules.{file}.exports` | string[] | 同层 frontend 任务 | API 模块的真实导出函数名（含参数提示）。同层任务验证 `import {X} from '@/api/xxx'` 时对照此列表 |
| `api_modules.{file}.imported_by` | string[] | 同层 frontend 任务 | 哪些页面引用了此 API 模块。帮助判断交叉依赖 |
| `stores.{file}.state` | string[] | 同层 frontend 任务 | Pinia store 的 state 字段名 |
| `stores.{file}.actions` | string[] | 同层 frontend 任务 | Pinia store 的 action 函数名 |
| `stores.{file}.getters` | string[] | 同层 frontend 任务 | Pinia store 的 getter 名 |
| `stores.{file}.imported_by` | string[] | 同层 frontend 任务 | 哪些页面引用了此 store |

**同层依赖**: 各 frontend 任务互不依赖（独立模块）。真理的 api_modules 和 stores 供同层交叉验证用。

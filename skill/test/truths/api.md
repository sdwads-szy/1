# api 真理提取

本层产出路由契约。

**上层**: backend_proc（method/path/request_fields/response）、nfr（端点列表）。
**同层**: 鉴权链——t_api_auth 产出 token_config，其余 api 任务通过 dependencies 获取已验证的 token 格式。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "routes": [{
      "file": "routes/auth.js",
      "basePath": "/api/auth",
      "handlers": [
        {
          "method": "POST",
          "path": "/register",
          "handler": "register",
          "middleware": [],
          "request_fields": ["phone", "password", "smsCode"],
          "response": {"success": true, "data": {"token": "string", "refreshToken": "string", "user": {"userId": "number", "mobile": "string", "nickname": "string", "avatar": "string", "role": "string('user'|'merchant'|'admin')"}}},
          "error_codes": ["INVALID_PHONE", "INVALID_PASSWORD_FORMAT", "SMS_CODE_INVALID", "PHONE_REGISTERED", "REGISTER_FAILED"]
        },
        {
          "method": "POST",
          "path": "/login",
          "handler": "login",
          "middleware": [],
          "request_fields": ["phone", "password"],
          "response": {"success": true, "data": {"token": "string", "refreshToken": "string"}}
        },
        {
          "method": "POST",
          "path": "/send-sms",
          "handler": "sendSms",
          "middleware": [],
          "request_fields": ["phone"],
          "response": {"success": true}
        },
        {
          "method": "POST",
          "path": "/refresh",
          "handler": "refreshToken",
          "middleware": [],
          "request_fields": [],
          "response": {"token": "string", "refreshToken": "string"}
        }
      ]
    }]
  },
  "exposed_to_peers": {
    "token_verified": true
  }
}
```

🛑 一个路由文件含多个 handler——每个都要在 `handlers[]` 中列出。上面 routes/auth.js 含 register/login/send-sms/refresh 四个 handler，全列出来了。
🛑 **response 展开铁律**：`response.data` 中的嵌套对象必须展开到叶子字段，禁止写 `"user": "object"` 或 `"data": {}`。从 controller 源码 `response.success(res, {...})` 或 `res.json({...})` 的实参中逐字段提取，标注类型。

### exposed_to_upper

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `routes[].file` | string | backend_proc | 路由文件路径 |
| `routes[].basePath` | string | backend_proc | API 前缀 |
| `handlers[].method` | string | backend_proc | GET/POST/PUT/DELETE |
| `handlers[].path` | string | backend_proc | 路由路径 |
| `handlers[].handler` | string | backend_proc | controller 函数名 |
| `handlers[].middleware` | string[] | nfr | 中间件函数名 |
| `handlers[].request_fields` | string[] | backend_proc | 🛑 controller 接收的 body 字段名数组 |
| `handlers[].response` | object | backend_proc, frontend | 🛑 controller 成功响应的完整 data 结构。**嵌套对象必须展开到叶子字段**，禁止写 `"user": "object"`。必须从 controller 源码 `response.success(res, {...})` 逐字段提取，含类型标注。 |
| `handlers[].error_codes` | string[] | api | 🆕 controller 的 errorMapping key 列表。A 用这些精确值断言，禁止编造 |

### exposed_to_peers（同层鉴权链）

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `token_verified` | bool | 同层 api 任务 | t_api_auth 产出 → 其余 t_api_* 通过 dependencies 获取。为 true 表示 JWT 签名/验证/注入已通过，同层任务可直接信任鉴权 |

**同层传递路径**: `t_api_auth` 产出 token_verified=true → `t_api_order` 依赖 t_api_auth → 调度器注入 t_api_auth 的同层真理 → t_api_order 信任鉴权已通过，不再重复验证 token 格式。

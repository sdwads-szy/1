# api 测试模板 — 参数化接口契约验证

🛑 **禁止 supertest、禁止 require('../../app')、禁止数据库连接**。
🛑 `fs.readFileSync` + `toContain`，所有断言值从真理 JSON 提取。

## 第一步：从真理提取参数

在 `## 🥇 下层真理` 的 `@truth t_api_*` → `routes[].handlers[]` 中提取：

```
{ROUTE_FILE}     ← routes[].file                    如 "routes/auth.js"
{CTRL_FILE}      ← 同路径 controllers/XController    如 "controllers/authController.js"
{BASE_PATH}      ← routes[].basePath                 如 "/api/auth"
{HANDLERS}       ← handlers[] 数组，每个含:
  {METHOD}       ← .method                          如 "POST"
  {PATH}         ← .path                            如 "/register"
  {HANDLER}      ← .handler                         如 "register"
  {MIDDLEWARE}   ← .middleware                      如 ["authenticate"]
  {REQ_FIELDS}   ← .request_fields                  如 ["phone","password","smsCode"]
  {ERROR_CODES}  ← .error_codes                     如 ["PHONE_REGISTERED","SMS_CODE_INVALID",...]
{FRONT_API_FILE} ← 前端 targetFiles[0]               如 "src/api/auth.js"
{FRONT_ENDPOINTS}← @truth t_frontend_* → api_calls   如 ["POST /auth/login",...]
```

🛑 **铁律：上面每个值从真理 JSON 逐字抄。真理 method 是 `POST` 就写 `POST`。真理 error_codes 是 `PHONE_REGISTERED` 就写 `PHONE_REGISTERED`，禁止编造 `PHONE_EXISTS`。**

## 第二步：按 scenario category 选维度

| category | 启用维度 |
|:---:|------|
| correct | 维度1(路由) + 维度2(字段) + 维度5(响应) + 维度6(前端对齐) |
| auth | 维度3(中间件) |
| error | 维度4(错误码) |

## 第三步：填入骨架

```javascript
const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('{TASK_ID}', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, '{ROUTE_FILE}'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, '{CTRL_FILE}'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, '{FRONT_API_FILE}'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    // 🛑 每个 handler 1 个 it()
    {ROUTE_ITEMS}
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    // 🛑 每个 handler 的 request_fields
    {FIELD_ITEMS}
  });

  // ==== 维度3: 中间件链（仅 auth category）====
  describe('中间件链', () => {
    {MIDDLEWARE_ITEMS}
  });

  // ==== 维度4: 错误码映射（仅 error category）====
  describe('错误码映射', () => {
    // 🛑 error_codes 是字符串数组，逐码 toContain。禁止编造
    it('controller 包含所有契约错误码', () => {
      const codes = {ERROR_CODES_ARRAY};
      codes.forEach(c => expect(ctrlSrc).toContain(c));
    });
  });

  // ==== 维度5: 响应格式 ====
  describe('响应格式', () => {
    it('controller 使用规范响应方法', () => {
      const usesResponse = ctrlSrc.includes('response.success')
                        || ctrlSrc.includes('response.fail')
                        || ctrlSrc.includes('response.error')
                        || ctrlSrc.includes('res.json(')
                        || ctrlSrc.includes('res.status(');
      expect(usesResponse).toBe(true);
    });
  });

  // ==== 维度6: 前端对齐 ====
  describe('前端对齐', () => {
    it('前端 API 调用的端点与后端路由一致', () => {
      const endpoints = {FRONT_ENDPOINTS_ARRAY};
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});
```

**{ROUTE_ITEMS} 填充规则：**
```javascript
// 真理 handlers[]: [{method:"POST", path:"/register", handler:"register"}, ...]
it('POST /register → handler: register', () => {
  expect(routeSrc).toContain('/register');
  expect(ctrlSrc).toContain('register');
});
it('POST /login → handler: login', () => {
  expect(routeSrc).toContain('/login');
  expect(ctrlSrc).toContain('login');
});
// ... 每个 handler 1 个 it()
```

**{FIELD_ITEMS} 填充规则：**
```javascript
// 真理 request_fields: ["phone","password","smsCode"]
it('controller 接收了预期字段: phone, password, smsCode', () => {
  ['phone', 'password', 'smsCode'].forEach(f => expect(ctrlSrc).toContain(f));
});
```

**{MIDDLEWARE_ITEMS} 填充规则：**
```javascript
// 真理 middleware: ["authenticate"] — 空数组则断言不含 authenticate
it('路由挂载了 authenticate 中间件', () => {
  expect(routeSrc).toContain('authenticate');
});
// 无中间件的路由:
it('/refresh 为公开端点，不含 authenticate', () => {
  // 找到 /refresh 所在行，确认该行无 authenticate
});
```

**{ERROR_CODES_ARRAY} 填充规则：**
```javascript
// 🛑 从真理 error_codes 逐字抄
['INVALID_PHONE', 'INVALID_PASSWORD_FORMAT', 'SMS_CODE_INVALID', 'PHONE_REGISTERED', 'REGISTER_FAILED']
```

🛑 只用 toContain，不写复杂正则。前端 API 路径不带 `/api` 前缀（baseURL 已设）。

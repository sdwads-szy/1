# b: api 层 — 测试代码诊断

B 只判断测试代码是否正确。api 层测试只验证请求↔响应对齐。

## 检查链

### 1. Token 注入
- 缺 `Authorization: Bearer ${token}` → 401 → `fix_target=test`
- token 从 `t_api_auth` 的 produces 注入，不应硬编码

### 2. 请求字段与契约对齐
- `.send({address_id: 1})` → snake_case → `fix_target=test`
- 字段名必须与契约 requestBody 一致（camelCase）

### 3. 响应断言与契约对齐
- `expect(res.body.data.order_id).toBeDefined()` → snake_case + 弱断言 → `fix_target=test`
- 应与契约 response 字段一致: `res.body.data.orderId`

### 4. 分页断言格式
- 列表接口必须验证 `{list, total, page, pageSize}` 结构

### 5. 测试框架
- api 层用 jest + supertest (CJS)，出现 `import`/`vi.mock` → `fix_target=test`

### 6. Mock 完整性
- 外部 API 调用（支付/短信/物流）必须在 mockSpec 中覆盖
- 本地 DB/service 已由 infra+backend 验证，不需额外 mock

## 判定
以上全部干净，测试仍失败 → `fix_target=source`（源码路由未挂载/字段不对齐）

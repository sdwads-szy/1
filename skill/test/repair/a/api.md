# a: api 层 — 测试修复

## ban 解读
api 层的 ban 指向测试中端点请求/响应字段对齐问题。

## 修复策略

### 缺 Authorization
- 治法：在 beforeAll 中从 t_api_auth 获取 token
- 每个请求补 `.set('Authorization', 'Bearer ${token}')`

### 字段名不对齐 (ALIGN/MISMATCH)
- 请求体字段蛇形→驼峰或反向：`address_id` → `addressId`
- 治法：对齐 api 契约 requestBody 中定义的字段名，改测试中的 `.send({...})`

### 响应断言字段错
- `expect(res.body.data.order_id)` → `expect(res.body.data.orderId)`
- 治法：逐字段对齐 api 契约 response.200.data 中的字段名

### 分页断言缺字段
- 治法：补 `{list, total, page, pageSize}` 完整 toMatchObject

### 错误码断言缺失
- 治法：加异常路径测试 → 验证 `res.status === 422/409/403` + `res.body.code`

## 工具选择（优先 edit_batch）
- 缺 header / 字段名错 / 断言缺 → `edit_batch` 精准修
- 多处结构性崩塌 → `create_file` 重写

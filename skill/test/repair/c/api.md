# c: api 层源码修复

## 下层真理（不可质疑 —— 来自 bans_text）
- **infra**: DB/Redis 可用 ← 不怀疑连接
- **db**: 表结构正确 ← 不怀疑是数据库问题
- **backend**: controller 导出函数名绝对正确 ← require 用正确名，路由 handler 名对齐
- **同层 api**: 前置 api 任务已通过的端点格式 ← consumes 引用的 token/userId/orderId 格式正确

## 输入输出对齐（api 层的核心工作）
```
请求端输出  → api（本层）→ 响应端输出
  backend 函数签名:  login(req,res) → router.post('/login', login)
  db-api SQL 签名:   findByPhone(encryptedPhone) → controller 调用参数对齐
  同层 produces:     t_api_auth → {token, userId} → t_api_order 用这些做 Authorization
```

## 修复策略

### 字段名不匹配（最高频）
下层真理已锁定 API 契约的字段名。本层代码的字段必须对齐真理。
```js
// 真理说 req.body 应有 phone → 代码接收 phone（不用 phoneNumber/mobile）
// 真理说 response.data 应有 userId → res.json({data:{userId}})，不用 user_id
```
**改任一边对齐真理即可。不关心业务含义。**

### 路由未挂载
对照 backend 真理中的 controller 导出清单，在 app.js 中挂载对应路由。
```js
const xxxRoutes = require('./routes/xxx');
app.use('/api/xxx', xxxRoutes);
```

### 错误码映射错
```js
catch (err) {
  if (err.message === 'INSUFFICIENT_STOCK') return response.fail(res, '库存不足', 422);
  // ...对齐 logic 契约 errorMapping
}
```

### 同层 consumes 对齐
若 consumes 引用了同层其他 api 任务的 produces，格式严格对齐：
- token: `Bearer <JWT三段式>`
- userId: int 正整数
- orderId: int 正整数

### 工具选择
- 整个 controller 多处字段名需改 → `create_file` 重写
- 只改 1-2 行字段名 → `edit_files` 精准修

# a: NFR 层 — 测试修复

## ban 解读
NFR 层测试验证性能/安全/并发。ban 指向框架选择/payload强度/并发模拟问题。

## 修复策略

### 框架选错
- jest 测 QPS → 改为 k6/autocannon（jest 单线程无法模拟并发）
- 安全测试仍用 jest+supertest

### SQL 注入 payload 弱
- 正常 keyword → `"' OR 1=1 --"`, `"1; DROP TABLE--"` 等标准载荷

### Token 篡改测试弱
- 未真正篡改 → `jwt.sign({...}, 'wrong_secret')` 错误密钥
- 改 payload 后签名 → 验证 verify 失败

### 并发模拟不足
- 单线程顺序请求 → `Promise.all([req1, req2])` 同时发起
- 验证只有一个成功，另一个返回冲突

## 工具选择（优先 edit_batch）
- payload 补强 / 并发模拟 → `edit_batch` 精准修
- 框架替换 / 结构性崩塌 → `create_file` 重写

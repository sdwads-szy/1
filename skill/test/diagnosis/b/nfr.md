# b: NFR 层 — 测试代码诊断

## 检查链

### 1. 框架检查
- NFR 用 jest 测 QPS → 单线程无法模拟并发 → `fix_target=test`
- 性能测试用 k6/autocannon，安全测试用 jest+supertest

### 2. 安全 payload
- SQL 注入用正常 keyword → 无攻击效果 → `fix_target=test`
- 应使用 `"' OR 1=1 --"` 等标准攻击载荷
- Token 篡改用 `jwt.sign({...}, 'wrong_secret')` → 错误密钥

### 3. 并发模拟
- 测试需模拟 ≥2 并发请求同时扣同一 SKU
- 单线程顺序请求 → `fix_target=test`

## 判定
以上全部干净，测试仍失败 → `fix_target=source`

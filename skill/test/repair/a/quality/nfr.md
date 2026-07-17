# A repair: nfr

A 的测试代码被 B 判定 `fix_target=test` → A 自我修复。

## 判定：删了重写 vs 修补

| 情况 | 动作 | 工具 |
|------|------|------|
| 用 jest 测 QPS/并发压测 | **重写** | `create_files` 加载 [模板](../../../templates/quality/nfr.md) 全新生成，性能用 k6/autocannon |
| SQL 注入 payload 太弱（如只用 `OR 1=1`） | **修补** | `edit_batch` 改为 `'; DROP TABLE--` 等标准载荷 |
| XSS 断言了 res.body 而非 res.text | **修补** | `edit_batch` 改为 `res.text` |
| RateLimit 只发了少量请求（<50） | **修补** | `edit_batch` 补到至少 50 并发 |
| 并发用 await 顺序发而非 Promise.all | **修补** | `edit_batch` 改为 `Promise.all` |
| 攻击载荷期望了精确 status（如 400） | **修补** | `edit_batch` 改为 `not.toBe(500)` 安全拦截 |
| 缺某个安全维度（SQL注入/XSS/CORS/Token 任一） | **修补** | `edit_batch` 补对应 describe |
| 缺 CORS Origin 测试 | **修补** | `edit_batch` 补 OPTIONS + Origin 头 |

🛑 修复后对照 [测试点表](../../roles/a/quality/nfr.md) 确认安全 ≥4 + 超频 ≥1 + 并发 ≥1。

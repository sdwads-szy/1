# nfr 真理提取

本层产出质量验证结果。按 NFR 类型消费不同上游：
- 端点型(性能/并发/SQL注入/限流/可用性) → scenario(chains[].endpoints[])
- 页面型(XSS) → scenario(chains[].pages[]) + navigation(jumps[])
- 配置型(HTTPS/CORS) → infra
- Token → auth

**上层**: 无（终端层）。
**同层**: 各 nfr 任务独立（安全/性能/并发/限流/Token 互不依赖）。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "security": {
      "sql_injection": "parameterized_only",
      "xss": "output_encoding",
      "auth_bypass": "middleware_enforced",
      "encryption": "AES-256-CBC + bcrypt_10_rounds"
    },
    "rate_limit": {"max": 100, "window": "1m"},
    "concurrency": {"lock": "SELECT_FOR_UPDATE", "idempotency": "token_based"}
  },
  "exposed_to_peers": {}
}
```

### exposed_to_upper

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `security.sql_injection` | string | — | SQL 注入防护策略 |
| `security.xss` | string | — | XSS 防护策略 |
| `security.auth_bypass` | string | — | 鉴权绕过防护结果 |
| `security.encryption` | string | — | 加密算法和轮数 |
| `rate_limit.max` | int | — | 限流阈值 |
| `rate_limit.window` | string | — | 限流时间窗口 |
| `concurrency.lock` | string | — | 并发锁策略 |
| `concurrency.idempotency` | string | — | 幂等策略 |

### exposed_to_peers

空。各 nfr 任务独立验证不同质量维度。

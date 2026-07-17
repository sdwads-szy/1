# auth 真理提取

本层产出 JWT Token 配置。

**上层**: api（token 格式）、nfr（测 token 过期/伪造）。
**同层**: auth 只有一个任务（t_auth_token），无同层依赖。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "token_config": {
      "secret_env": "JWT_SECRET",
      "expiresIn": "2h",
      "refreshExpiresIn": "7d",
      "injection": "req.user = {userId, role, iat, exp}"
    }
  },
  "exposed_to_peers": {}
}
```

### exposed_to_upper

| 字段 | 类型 | 写给谁 | 说明 |
|------|------|--------|------|
| `secret_env` | string | nfr | JWT 密钥的环境变量名 |
| `expiresIn` | string | nfr | access token 过期时间 |
| `refreshExpiresIn` | string | nfr | refresh token 过期时间 |
| `injection` | string | api | 🛑 认证后注入 req 的字段 |

### exposed_to_peers

空。auth 层仅一个任务。

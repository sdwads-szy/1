# C: nfr — 安全/性能修复

继承 [quality.md](../quality.md) 通用规则。nfr 修的是中间件/安全配置/索引/连接池。

## 🛑 真理定位

修复前根据 NFR 类型查对应真理：
- **端点型** → scenario 真理 `chains[].endpoints[]` 确认端点路径/method/request_fields
- **页面型** → scenario 真理 `chains[].pages[]` + navigation 真理 `jumps[]`
- **配置型** → infra 真理
- **Token 型** → auth 真理 `token_config`

## 修复策略

```
SQL_INJECTION → 字符串拼接 SQL 改为参数化查询（?占位符 + 参数数组）
XSS_UNESCAPED → 输出处加转义: escapeHtml() 或 res.text 用 textContent
CORS_OPEN → app.js 加 cors({origin: whitelist}) 中间件
WEAK_EXPIRY → jwt.verify 去掉 ignoreExpiration，确保检查 exp
NO_RATE_LIMIT → app.js 加 express-rate-limit: windowMs=10000, max=20
NO_SIZE_LIMIT → express.json({limit:'1mb'})
CONCURRENCY_OVERSELL → service SQL 加 FOR UPDATE 或乐观锁 WHERE version=
```

## 反作弊

```
□ 不能降低 QPS 阈值来通过 → CHEAT
□ 不能把攻击载荷改为正常输入 → CHEAT（改测试文件）
□ 不能删限流中间件 → CHEAT
```

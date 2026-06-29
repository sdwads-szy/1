# d: infra 层 — 源码验证

## 验证步骤
1. 跑测试 → 全过 → 基础设施可用 → 完成
2. 仍有失败 → 区分：环境问题(scheduler 自动修) vs 源码问题(C 修)

## C 常见错误
| 错误 | 检测方式 | ban 指向 |
|------|---------|---------|
| 改了 .env 但没改 .env.example | 四件套变量集不一致 | 同步四文件 |
| 补了 package.json 依赖但没 npm install | MODULE_NOT_FOUND 仍出现 | npm install |
| module.exports 嵌套多余 | `response.success is not a function` | 改为 `module.exports = response` |
| 改了端口/主机但其他配置没同步 | DB/Redis 连接拒绝 | 统一连接信息 |

## 反作弊
- C 删了 utils/response.js 的错误处理分支 → `fix_target=source` + CHEAT
- C 把 db.js 的 pool 改成 {} 空对象 → `fix_target=source` + CHEAT

## 判定矩阵

| 失败 | 源码问题 | 修复 |
|------|---------|------|
| `Cannot find module 'express'` | package.json 缺依赖 | npm install |
| `ECONNREFUSED` | .env 连接信息错 | 修正 host/port |
| `response.success is not a function` | module.exports 嵌套 | 去掉嵌套 |
| `db.query is not a function` | config/db.js 未导出 | 补全导出 |
| `.env` 变量集不一致 | 四文件缺/多变量 | 以 .env.example 为准 |
| `.env` 中第三方服务变量为空 | 正常！Agent 不知道真实API Key | **不修**，告知测试放宽 |

## 关键规则：空 env 变量不是错误
- OSS_* / WECHAT_* / ALIPAY_* / SMS_* / *_API_KEY / *_APP_SECRET 等第三方服务变量**允许为空**
- Agent 不可能生成真实密钥，空值是**正确状态**
- 测试若因此失败 → `fix_target=test`（测试太严，需放宽），不要浪费 C 的 attempt

# A: nfr — 质量层安全+性能测试

继承 logic 层通用规则。代码模板见 [templates/quality/nfr.md](../../../templates/quality/nfr.md)（jest+supertest）和 [templates/quality/nfr_k6.md](../../../templates/quality/nfr_k6.md)（k6 压测）。

🛑 攻击载荷被拦截 = correct（正确行为），不是 error。
🛑 安全测试验证"不崩溃"（status !== 500），不验证精确 status。
🛑 并发真实压测用 k6/autocannon，jest 单线程只能测 2 并发。

🛑 **端点型 NFR 只依赖 scenario 真理**（`chains[].endpoints[]`），页面型加 navigation，配置型加 infra/auth。

## 工作流

1. 读 testScenarios → 确定攻击类型/并发参数
2. 读 scenario 真理 `chains[].endpoints[]` → 🛑 端点路径/method/request_fields/auth_required
3. 按模板提取参数 → 填入骨架
4. create_files 输出

## 场景→模板映射

| 测试类型 | 模板 |
|---------|------|
| SQL注入/XSS/CORS/Token/RateLimit | [nfr.md](../../../templates/quality/nfr.md) |
| k6 压测/并发超卖 | [nfr_k6.md](../../../templates/quality/nfr_k6.md) |

## 独有规则

- correct category = 安全拦截（攻击被防御），不是 error

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/logic/nfr.md](../../../repair/a/logic/nfr.md)。

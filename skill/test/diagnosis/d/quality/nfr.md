# D: nfr — 源代码诊断 + 修复验证

🛑 通用规则见 [../logic.md](../logic.md)。

## 角色

D 是 nfr 层**源代码分析专家**。nfr 是质量层——安全漏洞在中间件/路由/配置中。B 加载 D 写 source ban，D 验证 C 的修复。

## 职责一：源代码根因分析（供 B 加载）

### 源码断点定位

| 测试症状 | 源码根因 | 断点位置 |
|---------|---------|---------|
| SQL 注入 payload 未被拦截 | 字符串拼接 SQL：`"SELECT * WHERE name='" + req.query.name + "'"` | 路由/controller 的 SQL 拼接行 |
| XSS payload 原样输出 | 输出处未转义 | 响应输出行 |
| 非白名单 Origin 通过 CORS | 缺 CORS 中间件或白名单为空 | app.js |
| 过期 token 仍能认证 | jwt.verify 有 `ignoreExpiration: true` | middleware/auth.js |
| 无 429 限流 | 缺限流中间件或 max 值过大 | app.js |
| 超大 body 未被拒绝 | 缺 `express.json({limit})` | app.js |
| 并发超卖 | SELECT 缺 FOR UPDATE | service SQL |

### C 常见改错方式（B 用来写 ⚠️C注意）

| C 错误 | 为什么错 | ⚠️预警 |
|--------|---------|--------|
| 只改一处 SQL 拼接 | 攻击者不只会攻击一个接口 | 全局搜索 `"SELECT.*\+ req\.` |
| 降低 QPS 阈值 | 测试通过但生产无保护 → CHEAT | 阈值与契约一致 |
| 把攻击载荷改为正常输入 | 修改测试文件 → CHEAT | 永远不改测试输入 |
| 加参数化但漏 LIKE % | `WHERE name LIKE ?` 传 `keyword` 而非 `%keyword%` | %放在参数值中 |
| CORS 配 `origin:'*'` + `credentials:true` | 浏览器禁止此组合 | 指定具体 origin |

### 防作弊底线

```
□ 降低 QPS 阈值 → CHEAT
□ 把攻击载荷改为正常输入 → CHEAT(fix_target=test)
□ 删了限流中间件 → CHEAT
□ 加 try-catch 吞掉注入异常 → CHEAT
```

---

## 职责二：验证 C 的修复

### 分类判定

| 分类 | nfr 层特征 |
|------|----------|
| UNCHANGED | 加了参数化但漏了一处 / CORS 白名单配错 |
| REGRESSION | 改中间件导致正常请求也失败 / 参数化后搜索无结果 |
| DEGRADED | 新安全漏洞（之前未测到的注入点） |
| CHEAT | 降低 QPS 阈值 / 改测试输入 / 删限流中间件 |

### 验证步骤

**1. 变更分析** — C 改了哪些中间件/路由/配置？

**2. 逐条验收** — 安全拦截=correct。

**3. 回归扫描**:

| 高频 REGRESSION | 检测方法 |
|---------------|---------|
| 改中间件导致正常请求失败 | 用正常输入重跑 correct |
| 参数化后搜索结果不对 | LIKE %位置检查 |
| CORS 配太严 | 白名单是否含合法 Origin |

**4. 意图分析** — nfr 层 CHEAT 高频，需重点检测。

**5. 二次指导**:

| 分类 | 二次指导 |
|------|---------|
| UNCHANGED | 列出所有字符串拼接 SQL 行号 + 逐条参数化 |
| REGRESSION | 中间件正确条件限定 |
| CHEAT | 回滚 + 恢复安全配置 + ⚠️ 安全不可妥协 |

## 🛑 最终响应（JSON 必须用 `<!--FINAL-->` 包裹）

**C 全部修对 → 真理：**
```
<!--FINAL-->
{
  "verified": true,
  "bans_resolved": ["#1"],
  "regressions": 0,
  "new_errors": 0
}
<!--FINAL-->
```

**C 仍有问题 → ban 数组：**
```
<!--FINAL-->
[
  {"f": "nfr|source|{file}:{行号}|{分类}", "b": "DON'T: {C做了什么}导致{测试失败} | C改动: {C的变更} | B要求: {B的fix} | fix: {二次修复代码} | ⚠️ C注意: {预警} | target=source"}
]
<!--FINAL-->
```
🛑 分类: UNCHANGED / REGRESSION / DEGRADED / CHEAT
🛑 CHEAT 必须含三要素分析（动机+影响+替代）
🛑 输出后立即停止，不要再调工具。

### D Ban 格式

```
f=nfr|source|{file}:{行号}|{分类}
b=DON'T: {C做了什么}导致{什么测试失败}
| C改动: {C的代码变更}
| B要求: {B原始ban的fix}
| fix: {第二次修复的完整代码}
| ⚠️ C注意: {风险预警}
| target=source
```

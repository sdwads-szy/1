# a: scenario 层 — 测试修复

## ban 解读
scenario 层测试验证端到端全链路。ban 指向上下文注入/依赖声明/异常流 mock 问题。

## 修复策略

### context 硬编码
- token/orderId 硬编码 → 声明 `consumes` 从依赖任务获取
- 治：beforeAll 中读 `t_scenario_buyer_checkout` 的 produces

### 枝干缺依赖
- 枝干 scenario 未声明 `dependencies: [scenario_main_trunk]`
- 治：补 dependencies，确保主干先通过

### 异常流未 mock
- exceptionFlows 中外部调用无 mock → nock 拦截
- 治：`nock('https://api.external.com').post('/callback').delay(60000).reply(408)`

### 步骤断言缺失
- 只验证最终状态不验证中间步骤 → 补每步关键断言
- 治：每步验证 `response.status` + 关键字段

## 工具选择（优先 edit_batch）
- 上下文注入 / 依赖声明 / 异常流 mock → `edit_batch` 精准修
- 结构性崩塌 → `create_file` 重写

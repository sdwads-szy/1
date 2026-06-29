# b: scenario 层 — 测试代码诊断

## 检查链

### 1. 上下文注入
- 硬编码 token/orderId → 不可靠 → `fix_target=test`
- 应用 `consumes` 从依赖任务注入上下文

### 2. 枝干依赖
- 枝干 scenario 必须声明 `dependencies: [scenario_main_trunk]`
- 缺依赖声明 → `fix_target=test`

### 3. 异常流 mock
- exceptionFlows 中外部调用必须 mock（支付/短信/物流 API）
- 缺 mock → 真实调用超时 → `fix_target=test`

### 4. 步骤断言
- 端到端场景每步验证 `response.status` 和关键字段
- 只验证"走通"不验证中间态 → `fix_target=test`

## 判定
以上全部干净，测试仍失败 → `fix_target=source`

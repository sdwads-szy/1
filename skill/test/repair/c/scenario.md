# c: scenario 层 — 源码修复

## 下层真理（不可质疑 — 来自 bans_text）
- **所有下层**: 单步接口/业务流程/权限都正确 — scenario 断了一定是本层的编排问题

## 输入输出对齐
```
下层输出 → scenario 输入:
  api 端点格式已验证 → scenario 调用时 method+path+body 对齐
  logic 步骤链已验证 → scenario 按步骤顺序编排，不跳步
  auth token 格式已验证 → scenario 上下文传递时 token 格式正确
同层 scenario:
  t_scenario_buyer_checkout → produces token/userId/orderId → 枝干 scenario 消耗
```

## 修复策略

### 流程中断于第 N 步
- 查第 N 步对应的 api/logic 契约 → 接口返回值是否对齐
- 可能是前一步 provides 的字段名与后一步 expects 不一致

### 上下文传递断裂
- provides→dependsOn 链路：前一步 output 字段名 = 后一步 input 变量名
- 治法：统一字段名，或加字段映射

### 枝干依赖缺失
- 枝干 scenario 必须有 `dependencies: [scenario_main_trunk]`
- 治：补依赖声明

### 异常流未触发
- exceptionFlows 的 triggerCondition 必须在 mock 条件下可满足
- 治：检查 mock 是否正确模拟了异常条件

## 工具选择
- 流程编排多处错 → `create_file` 重写
- 单步字段不对齐 → `edit_batch`

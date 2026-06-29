# d: scenario 层 — 源码验证

## 验证步骤
1. 跑测试 → 全过 → 端到端流程走通 → 完成
2. 仍有失败 → 定位断在哪一步 → 该步对应哪个 api/logic 契约
3. 排查方向：上下文传递断裂？依赖未通过？异常流 mock 失效？

## C 常见错误
| 错误 | 检测方式 | ban 指向 |
|------|---------|---------|
| 只修了断点不修后续 | 第 N 步过了第 N+1 步挂 | 沿步骤链继续排查 |
| 改了 produces 没改 downstream consumes | 上下文传递 mismatch | 对齐 provides→dependsOn |
| 枝干 scenario 的 dependencies 被删除 | 枝干缺主干依赖 | 恢复 dependencies |
| 异常流 mock 过期（nock URL 变了）| 异常流超时 | 更新 nock URL |

## 反作弊
- C 把异常流步骤从 scenario 里删了 → `fix_target=source` + CHEAT
- C 把需要验证的 expects 字段改为宽松匹配 → `fix_target=test` + CHEAT

## 判定矩阵

| 失败 | 源码问题 | 修复 |
|------|---------|------|
| 流程中断于第 N 步 | 该步接口与契约不符 | 查 api/logic 契约 |
| 上下文传递断裂 | provides→dependsOn 未对齐 | 对前步 output→后步 input |
| 分支无法触发 | branches 未实现 | 检查 triggerAfterStep |
| 异常流未触发 | exceptionFlows 条件不满足 | 检查模拟条件 |

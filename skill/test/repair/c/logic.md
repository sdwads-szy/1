# C repair: 逻辑层

D 判定分类后 C 的二次修复策略。适用于 backend_proc / logic / scenario。nfr 已移至 [quality.md](quality.md)。

## UNCHANGED — 同 ban 再命中

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| backend_proc | 加了 beginTransaction 忘 commit/rollback | 检查 try-catch 完整性 |
| backend_proc | B ban 指向的代码行没改到 | 重读 B ban 的文件:行号 |
| logic | 只修下游没修上游 | 上下游数据对接处同时检查 |
| logic | 字段名两端仍不一致 | 全局搜索该字段所有引用 |
| scenario | 只修断点不修后续步骤 | 沿 process 链检查后续 |

## REGRESSION — 原来 PASS 现在 FAIL

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| backend_proc | 改 step3 SQL 改变了 mock 期望 | 检查 SQL 参数变化 |
| backend_proc | 加字段后原有断言 toMatchObject 失败 | 检查新字段是否影响旧断言 |
| logic | 改字段名导致其他功能失败 | 全局搜索该字段名 |

## DEGRADED — 新错误

| 层 | C 常见失误 | 纠正 |
|----|----------|------|
| backend_proc | 新加 INSERT 列名写错 | 对照 DDL 确认列名 |
| logic | 补偿方向写反 | UPDATE stock+quantity(恢复) vs stock-quantity(扣减) |
| logic | 幂等键字段名错 | 对照契约 idempotentKey |
| scenario | 新改字段类型不匹配 | 检查上下游数据传递处 |

## CHEAT

| 层 | 常见作弊 | 纠正 |
|----|---------|------|
| backend_proc | 删 beginTransaction/commit/rollback | 恢复事务 |
| backend_proc | 去掉 FOR UPDATE | 恢复 |
| backend_proc | 删异常处理 | 恢复 try-catch+rollback+throw |
| logic | 删状态检查 | 恢复 |
| logic | 跳过补偿步骤 | 恢复完整补偿链 |
| scenario | 删异常流步骤 | 恢复 |

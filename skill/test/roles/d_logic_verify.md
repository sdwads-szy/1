# 业务层修复验证 (D步骤 — backend_proc/logic/scenario/nfr)

C 修改了数据处理逻辑后，验证修复是否有效。

## 验证要点

1. **运行测试** — 重跑对应的业务验证 it() 块
2. **如果仍失败**:

```
数据仍未落库 → C 的 INSERT 修复不完整 → fix_target=source, 子类型=FIELD_NOT_PERSISTED
响应仍不一致 → C 没对齐返回值 → fix_target=source, 子类型=RESPONSE_MISMATCH
关联表仍遗漏 → C 漏了关联 INSERT → fix_target=source, 子类型=MISSING_RELATED_INSERT
功能链仍断裂 → C 没补充调用 → fix_target=source, 子类型=CHAIN_BREAK

C 改错了方向 (修之前对的地方现在错了) → fix_target=source, 子类型=DEGRADED
```

3. **如果全部通过**:
- 评分: 调用五维代码评分
- 劣化检测: 修复后评分显著下降 → 回滚到历史最佳版本
- 对照 truth 验证数据管道完整性

## ban 指纹

f = {layer}|source|{端点}|{子类型}
子类型: FIELD_NOT_PERSISTED / RESPONSE_MISMATCH / MISSING_RELATED_INSERT / CHAIN_BREAK / DEGRADED

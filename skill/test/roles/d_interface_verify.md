# 接口层修复验证 (D步骤 — auth/api/db_api/navigation)

C 修改了接口连接点后，验证修复是否有效。

## 验证要点

1. **运行测试** — 重跑对应的接口验证 it() 块
2. **如果仍失败**:

```
路径仍不匹配 → C 改错了路径 → fix_target=source, 子类型=PATH_MISMATCH
列名仍不一致 → C 没对齐 DDL → fix_target=source, 子类型=COLUMN_MISMATCH
passBy 仍混用 → C 改反了 → fix_target=source, 子类型=PASSBY_MISMATCH
Token 仍无效 → C 的 JWT fix 有问题 → fix_target=source, 子类型=TOKEN_INVALID
```

3. **如果全部通过**:
- 对照 truth 验证 C 修改后的接口声明是否与 truth 一致
- 确认前端 API URL 匹配后端路由路径
- 确认 navigation passBy 和参数名一致

## ban 指纹

f = {layer}|source|{端点}|{子类型}
子类型: PATH_MISMATCH / COLUMN_MISMATCH / PASSBY_MISMATCH / TOKEN_INVALID

# 静态层修复验证 (D步骤 — infra/db/frontend_static/peer_deps)

C 修改了文件内容后，验证修复是否有效。测试代码已是真理，失败一定是 C 没改对。

## 验证要点

1. **运行测试** — C 修了什么就重跑对应的 it() 块
2. **如果仍失败**:

```
语法仍有错 → C 引入了新语法错 → fix_target=source, 子类型=syntax
内容仍不符合预期 → C 没改到点子上 → fix_target=source, 子类型=UNCHANGED
C 改错了方向 (之前对的地方现在错了) → fix_target=source, 子类型=DEGRADED
```

3. **如果全部通过**:
- 确认 C 修改后的文件 node --check 通过
- 确认只修改了白名单内的文件
- 输出 verified=true

## ban 指纹

f = {layer}|source|{文件}|{子类型}
子类型: syntax / UNCHANGED / DEGRADED

## 与 B 的区别
B 判断"问题在测试还是源码"。D 已经知道"问题在源码" (B 判过了)，只需判断"C 改对了没"。

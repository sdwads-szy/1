# d: logic 层 — 源码验证

## 验证步骤
1. 跑测试 → 全过 → 业务流程正确 → 完成
2. 仍有失败 → 定位是步骤顺序错？事务边界？补偿缺失？并发控制？
3. B 已验证 mock 链/断言正确 → 失败一定是 C 的修改不对

## C 常见错误
| 错误 | 检测方式 | ban 指向 |
|------|---------|---------|
| 改了一个步骤忘了改后续步骤的顺序 | NthCalledWith 第 N+1 次不匹配 | 检查全部步骤链 |
| 补了 rollback 但 commit 写在了 rollback 之前 | 事务操作顺序错 | begin→try➝commit, catch➝rollback |
| 补了补偿但补偿逻辑写反 | 补偿方向错误 | 补偿应撤销副作用 |
| 实现乐观锁但 WHERE 条件写错 | UPDATE 条件不匹配 | WHERE version=expectedVersion |
| 改了错误码映射但忘记 throw | 错误码定义了但没抛 | `throw new Error('CODE')` |

## 反作弊
- C 把事务直接删了（去掉 beginTransaction/commit/rollback）→ `fix_target=source` + CHEAT
- C 把所有错误处理都删了只留成功路径 → `fix_target=source` + CHEAT
- C 把乐观锁降级为普通 UPDATE → `fix_target=source` + CHEAT

## 判定矩阵

| 失败 | 源码问题 | 修复 |
|------|---------|------|
| 事务未回滚 | 异常路径缺 rollback | catch 块补 rollback |
| 错误码映射错 | 按 errorMapping 返回 | 对齐契约 |
| 步骤顺序错 | steps 执行顺序不符 | 对齐 stepId 顺序 |
| 补偿未执行 | compensation 未触发 | 按契约补 |
| 并发未实现 | 乐观锁/悲观锁缺失 | WHERE version / FOR UPDATE |

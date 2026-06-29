# b: logic 层 — 测试代码诊断

## 检查链

### 1. Mock 事务方法
- logic 契约 transactionBoundary=true → mockSpec 必须含 [beginTransaction, commit, rollback]
- 缺 rollback → `fix_target=test`

### 2. 步骤顺序断言
- `expect(db.query).toHaveBeenCalled()` → 不验证顺序 → `fix_target=test`
- 应用 `toHaveBeenNthCalledWith(1, ...)` `toHaveBeenNthCalledWith(2, ...)` 锁死顺序

### 3. 错误码断言
- `expect(err.message).toContain('error')` → 不验证具体码 → `fix_target=test`
- 应抛出具体错误: `toThrow('INSUFFICIENT_STOCK')`

### 4. 并发测试 mock
- 乐观锁测试需 mock `affectedRows=0` 模拟冲突 → 缺 → `fix_target=test`

## 判定
以上全部干净，测试仍失败 → `fix_target=source`

# a: logic 层 — 测试修复

## ban 解读
logic 层测试验证业务流程步骤链/事务/补偿。ban 指向 mock 完整性和断言顺序问题。

## 修复策略

### mock 缺事务 API
- transactionBoundary=true → mockSpec 必须含 beginTransaction/commit/rollback
- 治：补 `db.beginTransaction = jest.fn()` 等

### 步骤断言弱
- `toHaveBeenCalled()` → `toHaveBeenNthCalledWith(1, ...)` 锁死步骤顺序
- 每个步骤用递增序号验证

### 错误码断言弱
- `toContain('error')` → `toThrow('INSUFFICIENT_STOCK')` 具体错误码

### 补偿未 mock
- 异常路径需 mock 外部调用为 rejected → 触发 compensation 分支
- 治：`mockFn.mockRejectedValue(new Error('REMOTE_FAILED'))`

## 工具选择（优先 edit_batch）
- 缺 mock / 断言弱 / 错误码 → `edit_batch` 精准修
- 结构性崩塌 → `create_file` 重写

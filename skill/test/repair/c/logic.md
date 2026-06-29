# c: logic 层 — 源码修复

## 下层真理（不可质疑 — 来自 bans_text）
- **infra+db**: 环境+表结构正确 ← 不怀疑基础
- **api**: 端点请求/响应格式已锁定 ← 调 API 时的字段名/路径严格对齐
- **db-api**: SQL 签名正确 ← DAO 调用参数对齐真理签名
- **auth**: Token 格式+权限隔离正确 ← 不怀疑 role 校验逻辑

## 输入输出对齐
```
api 输出 → logic 输入:
  POST /api/orders → IN:{addressId, cartItemIds, payChannel} → 字段名严格一致
  response → OUT:{orderId, paymentId, payAmount} → 返回真理中的字段，不编造
db-api 输出 → logic 输入:
  findByPhone(encryptedPhone) → 参数名 'encryptedPhone' 不是 'phone'
```

## 修复策略

### 步骤顺序错
- 症状: `toHaveBeenNthCalledWith(N)` 不匹配 — 第 N 次调用不是预期的操作
- 原因: 函数体内代码顺序与 logic 契约 steps[].stepId 不一致
- 治: 重排代码顺序，严格对齐契约步骤链

### 事务未回滚
- 症状: 异常路径测试失败 — rollback 未被调用
- 原因: catch 块缺 rollback
- 治: `catch (err) { await db.rollback(); throw err; }`

### 错误码未映射
- 症状: 抛出了原始 DB 错误而非业务错误码
- 原因: catch 后未按 logic 契约 errorMapping 转换
- 治: `throw new Error('INSUFFICIENT_STOCK')` 对齐 errorMapping

### 补偿未执行
- 症状: 外部调用失败后补偿逻辑未触发
- 原因: catch 块中只有 rollback 没有 compensation
- 治: 按 steps[].compensation 补补偿动作

### 乐观锁未实现
- 症状: 并发测试超卖
- 原因: UPDATE 未带版本条件
- 治: `UPDATE ... SET stock=stock-? WHERE id=? AND stock>=?` → 检查 affectedRows

### API 调用字段名错
- 症状: 调用 api 层时传参字段名不匹配
- 原因: snaked_case vs camelCase
- 治: 对齐 api 真理中的请求/响应字段名

## 工具选择
- 步骤链/事务重构 → `create_file`
- 单错误码/单补偿补 → `edit_batch`

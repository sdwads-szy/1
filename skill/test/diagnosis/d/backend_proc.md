# d: backend_proc 层 — 源码验证

C 修改了 controller/service 的数据处理逻辑后，验证修复是否有效。

## 验证步骤

1. **请求→DB 数据管道完整性**
   - 对每个修改的写操作端点，重新发送 HTTP 请求
   - 查数据库验证：主表有新行？关联表有新行？行数正确？
   - 漏了 → C 没补全 → ban 标记 FIELD_NOT_PERSISTED

2. **响应→DB 一致性**
   - 比较 `response.data` 中的字段值与实际 DB 行的对应列值
   - 不一致（如 response 说 orderNo="xxx" 但 DB 是 "yyy"）→ ban 标记 RESPONSE_MISMATCH

3. **关联表写入**
   - POST /orders 后 order_items 是否有对应行？payments 是否有对应行？cart_items 是否清除？
   - 缺少 → ban 标记 MISSING_RELATED_INSERT

4. **副作用验证**
   - DELETE 操作后目标行是否真的不存在（或 status 变更）？
   - 没生效 → ban 标记 SIDE_EFFECT_MISSING

5. **劣化检测**
   - C 修改后是否引入了新的列名错误或事务问题？
   - 对比修复前后的 `node --check` 和 SQL 列名扫描

## ban 指纹格式

f = backend_proc|source|{端点}|{子类型}

子类型: FIELD_NOT_PERSISTED / RESPONSE_MISMATCH / MISSING_RELATED_INSERT / SIDE_EFFECT_MISSING

# backend_proc 层源码修复 (C步骤)

C 修改 controller/service 的数据处理逻辑。修复目标: HTTP 请求的字段正确到达 DB 列，响应字段与 DB 一致。

## 典型 ban → 修复动作

```
F IELD_NOT_PERSISTED:
  请求字段未写入 DB → 检查 controller 的 req.body 解构是否包含该字段
  → 检查 service 的 INSERT 列列表是否包含对应列
  → edit_batch 在 controller 中补充解构 或 service 中补充 INSERT 列

RESPONSE_MISMATCH:
  响应字段值与 DB 不一致 → 检查 service 返回值
  → 检查 controller 中 response.success(res, data) 的 data 对象
  → 对齐字段名: 如果 DB 列是 total_amount，响应可以是 totalAmount

MISSING_RELATED_INSERT:
  关联表遗漏 → 在主 INSERT 之后补充关联表的 INSERT 语句
  → 确保在同一事务内 (conn.execute)
  → 确保 FK 列值使用主 INSERT 的 insertId

SIDE_EFFECT_MISSING:
  DELETE 后目标行仍存在 → 检查 DELETE 语句的 WHERE 条件
  → 检查是否使用了 conn.execute (事务) 而非 db.query (连接池新连接)
```

## 禁止
- 不修改测试文件
- 不修改 truth 声明
- 不怀疑 B 的诊断结论
- 事务内禁止 db.query()，强制 conn.execute()

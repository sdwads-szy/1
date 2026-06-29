# db_api 层诊断 (B步骤)

诊断范围限定: Service SQL 列名 vs DDL 列名一致性、事务连接使用。

## 判定规则

```
total=0 + Unknown column 'xxx' → fix_target=source, 子类型=COLUMN_MISMATCH
total=0 + Column count doesn't match → fix_target=source, 子类型=COLUMN_COUNT
total>0 + 数据正确但测试期望的列名不存在 → fix_target=test, 子类型=WRONG_EXPECTATION
事务内出现 db.query() → fix_target=source, 子类型=TX_CONN_MISUSE
```

## 常见失败模式

1. "Unknown column 'product_name' in 'field list'" → DDL 中是 `title`，Service 写成了 `product_name` → COLUMN_MISMATCH
2. "Column count doesn't match value count" → INSERT 列列表 6 列但 VALUES 只有 5 个 → COLUMN_COUNT
3. conn.beginTransaction() 后的 INSERT 用了 db.query() 而非 conn.execute() → TX_CONN_MISUSE

## 禁止扩大到
- SQL 逻辑是否正确 (backend_proc层)
- 接口路径匹配 (api层)
- 业务规则 (logic层)

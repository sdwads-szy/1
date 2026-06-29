# db_api 层源码修复 (C步骤)

C 修改 Service 文件中的 SQL 语句。修复目标: SQL 列名全部对齐 DDL truth。

## 典型 ban → 修复动作

```
COLUMN_MISMATCH:
  SQL 中使用了 DDL 不存在的列名 → 查 DDL truth 找到正确的列名
  → edit_batch 替换: product_name → title, description → remark
  → 常见映射陷阱: name→title, image→images, channel→method, amount→total_amount

COLUMN_COUNT:
  INSERT 列数与 VALUES 数不匹配 → 对齐列列表和 VALUES
  → 检查是否遗漏了 NOT NULL 列或多了已删除的列

TX_CONN_MISUSE:
  事务体内用了 db.query() → 改为 conn.execute(sql, params)
  → 注意: db.query() 走连接池，拿的是另一个连接，不在事务中

OP_MISMATCH:
  db_api truth 声明 CRUD_READ 但写成了 INSERT → 改为 SELECT
```

## 修复方式
- 单列名错误 → edit_batch 精准替换
- 多处列名错误 → create_files 重写整个 SQL 函数
- DDL truth 是列名的唯一标准，不可质疑

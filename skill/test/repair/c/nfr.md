# c: NFR 层 — 源码修复

## 下层真理（不可质疑 — 来自 bans_text）
- **所有下层**: 功能完整，业务流程正确 — 性能/安全问题只可能在本层基础设施

## 输入输出对齐
```
下层输出 → NFR 输入:
  logic 并发策略已验证 → NFR 压测已知的并发瓶颈点
  api 端点格式已验证 → NFR 安全测试构造的攻击请求格式正确
  db 表结构已验证 → NFR 不需要怀疑索引缺失是否因表结构问题
```

## 修复策略

### QPS 不达标
- 缺索引 → EXPLAIN 分析慢查询，补索引
- 缺缓存 → Redis 缓存热点数据
- 连接池太小 → 增大 poolSize

### P99 超标
- N+1 查询 → 批量查询
- 未分页 → 加 LIMIT/OFFSET
- 同步阻塞 → 异步处理

### SQL 注入
- 字符串拼接 SQL → 改为 `?` 占位符 + 参数数组
- 动态 ORDER BY → 白名单校验列名

### XSS
- 输出未编码 → HTML 实体编码
- 富文本未过滤 → DOMPurify/sanitize-html

### 并发超卖
- 乐观锁: `UPDATE ... SET stock=stock-? WHERE id=? AND stock>=?` → 检查 affectedRows
- 悲观锁: `SELECT ... FOR UPDATE` → 事务内加锁

## 工具选择
- 索引/缓存/连接池多处调整 → `create_file`
- 单查询改参数化 → `edit_batch`

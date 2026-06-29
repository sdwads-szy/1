# a: db 层 — 测试修复

## ban 解读
db 层测试直连真实数据库。ban 指向表名/断言/初始化问题。

## 修复策略

### 表名写错
- 测试中 `SHOW TABLES LIKE 'order'` → 应 `'orders'`（复数）
- 治法：对齐 model 契约 tableName

### 断言太弱
- `expect(row).toBeDefined()` → `expect(typeof row.id).toBe('number')`
- 索引断言：`expect(idx.length).toBeGreaterThan(0)`
- FK 断言：`expect(() => insert(...)).toThrow('ER_NO_REFERENCED_ROW_2')`

### 未执行 init-db
- 测试前需 `execSync('node scripts/init-db.js')` 在 beforeAll 中
- 或确保 seed 数据已准备

### ENUM 值域测试缺失
- 需插入非法值验证抛错：`INSERT ... VALUES ('invalid_enum_value')` → expect toThrow

## 工具选择（优先 edit_batch）
- 表名错 / 断言弱 → `edit_batch` 精准修
- 语法错 / 结构性崩塌 → `create_file` 重写

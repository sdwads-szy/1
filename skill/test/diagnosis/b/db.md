# b: db 层 — 测试代码诊断

B 只判断测试代码是否正确。db 层测试直连 MySQL 验证 DDL——测试干净但失败意味着 `database/*.sql` 的 DDL 不对齐 model 契约。

## 检查链

### 1. 语法
node --check → 不通过 → `fix_target=test`

### 2. 表名对齐
- 测试中 `SHOW TABLES LIKE 'order'` → 表名错（应是 'orders'）→ `fix_target=test`
- 对照 testScenarios[0].then 中的列名

### 3. 断言强度
- `expect(row).toBeDefined()` → 太弱 → `fix_target=test`
- 应验证具体类型: `expect(typeof row.id).toBe('number')`
- 对照 testScenarios.then 逐列验证类型/约束/默认值

### 4. Mock 完整性
db 测试直连真实数据库（.env 有 localhost），不需要 mock。若 mock 了 db 连接反而掩盖问题 → `fix_target=test`

### 5. 测试框架
db 层用 jest(CJS)，`require` + `jest.mock`。出现 `import`/`vi.mock` → `fix_target=test`

## 判定
以上全部干净，测试仍失败 → `fix_target=source`（`database/*.sql` 的 DDL 不对齐 model 契约，或 `init-db.js` 的 `SQL_FILES` 数组缺文件）

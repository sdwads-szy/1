# a: infra 层 — 测试修复

## ban 解读
infra 层测试验证环境基座。ban 指向 mock/路径/断言问题。

## 修复策略

### 缺 jest.mock
- npm 包(mysql2/ioredis/winston/bcryptjs/jsonwebtoken)必须在 jest.mock 工厂中覆盖
- 治法：补 `jest.mock('mysql2/promise', () => ({ createPool: jest.fn(), ... }))`

### require 路径错
- `require('config/db')` → 补 `../../config/db`
- `require('../utils/response')` → 中间件/下应 `../../utils/response`

### 断言太弱
- `expect(db).toBeDefined()` → `expect(typeof db.query).toBe('function')` 逐函数验证
- `expect(res).toBeTruthy()` → 验证 res.json 被调用的确切参数

### 语法错
- node --check 验证 → 不通过 → `create_file` 重写

## 工具选择（优先 edit_batch）
- 缺 mock / 路径错 / 断言弱 → `edit_batch` 精准修
- 语法错 / 结构性崩塌 → `create_file` 重写

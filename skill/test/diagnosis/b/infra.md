# b: infra 层 — 测试代码诊断

B 只判断测试代码是否正确。测试干净但测试仍失败 → `fix_target=source`，交给 C/D。

## 检查链

### 1. 语法 (node --check)
- `SyntaxError`, `Unexpected token` → `fix_target=test`

### 2. Mock 完整性
| 源文件引用了 | 测试必须 mock | 缺失时 symptom |
|------------|-------------|---------------|
| `require('winston')` | `jest.mock('winston',...)` | `TypeError: winston.createLogger is not a function` |
| `require('mysql2/promise')` | `jest.mock('mysql2/promise',...)` | `Cannot read property 'createPool'` |
| `require('ioredis')` | `jest.mock('ioredis',...)` | `ECONNREFUSED` |

→ 缺 mock → `fix_target=test`

### 3. require 路径
- `require('config/db')` 缺 `../../` → `fix_target=test`
- `Cannot find module '@/...'` → 别名不解析 → `fix_target=test`

### 4. 断言强度
- `expect(db).toBeDefined()` → 太弱 → `fix_target=test`
- 每个 `it()` 需 ≥2 个 `expect()`，验证具体值而非 typeof

### 5. 测试框架混用
- infra 层用 jest(CJS)，出现 `import`/`vi.mock` → `fix_target=test`

### 6. env 变量空值 ≠ 错误
- `.env` / `.env.development` 中第三方服务的环境变量**允许为空**
- 涉及 OSS_* / WECHAT_* / ALIPAY_* / SMS_* / 任何 API_KEY / APP_SECRET 类的变量 → Agent 不可能知道真实值
- 空值是**正确状态**，不是 bug
- 如果测试因为这类变量为空而失败 → `fix_target=test`（测试太严格，需放宽）

## 判定
以上全部干净，测试仍失败 → `fix_target=source`

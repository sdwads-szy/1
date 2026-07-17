# A: 逻辑层 — 通用规则

适用于: backend_proc / logic / scenario。**各子层的字段解读、测试点、独有规则在对应 `.md` 文件**。

## 通用流程

1. 读「任务数据（完整字段）」JSON → 了解 `sourceTask` / `dependencies`
2. 🛑 读 `## 🛑 下层真理` → 真理中有上游已验证的 services 函数签名（backend_proc 产出）+ routes 接口契约
3. 读「测试场景（验证集）」→ 场景给方向（测什么、什么 category），**不做精确值来源**
4. 按子层测试点逐条生成 it()，对照模板写代码——断言中的精确值从真理 JSON 取
5. 调 `create_files` 一次写完

🛑 **场景 vs 真理的分工**：
- 场景的 `scenario` 名 + `process` 步骤 → 理解业务流程方向
- 场景的 `category` → 确定启用哪些验证维度
- 场景的 `output` 字段值 → **示例/参考，不作为精确断言值**
- 🛑 精确值（函数名、参数、错误码、Redis key）**只从真理取**，不从场景取
- 🛑 如果真理写 `SMS_RATE_LIMIT` 而场景写 `TOO_MANY_SMS`，用真理的 `SMS_RATE_LIMIT`

🛑 写模式不调 edit_batch——逻辑层测试全新生成不修补。修模式（B 的 ban）才用 edit_batch 定点改。

## 🛑 工具调用规则

### 可用工具

| 工具 | 参数 | 模式 | 限次 | 说明 |
|------|------|:---:|:---:|------|
| **create_files** | `files` | 写+修 | 2 次 | 写/修测试代码，自带语法检查 |
| **edit_batch** | `files` | 仅修 | 不限 | 定点修改测试文件，自带语法检查 |
| **read_files** | 无 | 仅修 | 不限 | 读取测试文件（不含源码） |
| **install** | `packages` | 写+修 | 不限 | 缺 npm 包时用 |

🛑 模式判断：test 文件不存在 → **写模式**；test 文件已存在 + B 的 ban → **修模式**。

### 🛑 edit_batch 详解（仅修模式可用）

一次调用修改多个文件，每个文件可有多处编辑。行号 1-indexed。

```json
edit_batch(files=[
  {"file": "test/t_bp_register.test.js", "edits": [
    {"start": 47, "end": 46, "content": "  expect(rollback).toHaveBeenCalled();"}
  ]},
  {"file": "test/t_bp_register.test.js", "edits": [
    {"start": 30, "end": 32, "content": "it('should rollback on duplicate', async () => {\n  db.query.mockRejectedValueOnce(new Error('DUPLICATE_ENTRY'));\n  await expect(createOrder(userId, items)).rejects.toThrow('DUPLICATE_ENTRY');\n  expect(rollback).toHaveBeenCalled();\n});"}
  ]}
])
```

| 模式 | 条件 | 行为 |
|------|------|------|
| **插入** | `end < start` | 在 start 行**之前**插入 content |
| **替换** | `end >= start` | 把 start~end 行替换为 content |

🛑 同文件多处 → 一个 edits 数组；多文件 → 一个 files 数组。**绝对不要分两次调！**
🛑 调用后自动语法检查，语法错误返回 `WRITE REJECTED`。

### 🛑 create_files 详解（写+修模式）

一次调用创建/重写测试文件。content 是**完整文件内容**，不是增量。

```json
create_files(files=[
  {"path": "test/t_bp_register.test.js", "content": "const db = require('../config/db');\njest.mock('../config/db');\n...完整测试代码..."}
])
```

🛑 自动创建目录、覆盖已存在文件。多文件一次调用完成。**不要分两次调！**
🛑 两种使用场景：
  - **写**（新建）→ 直接写入完整测试文件
  - **修**（重写）→ 覆盖重写，修正后的完整内容重新写入
- 🛑 路径必须是 `test/{task_id}.test.js`，写其他路径会被拒绝
- 🛑 最多调 2 次。第 2 次仍失败 → 返回 false
- 返回 `WRITE REJECTED` → 语法错误，修正后重试
- 返回 `files 格式错误` → 参数结构不对

### 🛑 执行流程（根据模式动态调整）

**判断模式：**
- 🆕 test 文件不存在 → **写模式**
- 🔧 test 文件已存在 + B 的 ban → **修模式**

---

**写模式 — Step 1: 搜集（可选，全部工具一次并行调完）**
- 🛑 **禁止单独调**：如果不需要全部三个，至少把需要的在同一次响应中一起调
- 🛑 此步禁止 create_files
- 搜索失败/空结果 → 正常，不重试

**写模式 — Step 2: 写测试代码（必须）**
- 工具: `create_files`，**第一轮直接调，禁止先搜索再创建**
- 🛑 testScenarios 已含 input + process + output，模板提供 mock DB + 事务断言骨架
- 🛑 一次传完所有 it()

**写模式 — Step 3: 失败重写（1 次机会）**
- `WRITE REJECTED` / `files 格式错误` → 修正后重调 create_files
- 🛑 仅 1 次重写机会，仍失败 → 返回 false

---

**修模式 — Step 1: 读取（必须）+ 搜集（可选，一起调）**
- 工具: `read_files()` — **无参数**，只读测试文件（不含源码）
- 🛑 此步禁止 edit_batch / create_files

**修模式 — Step 2: 修复（必须）**
- 工具: `edit_batch`（定点改）**或** `create_files`（重写）
- 🛑 B 的 ban 已含文件:行号 + fix 指令，直接改

**修模式 — Step 3: 失败修复（1 次机会）**
- 修正后重调 edit_batch 或 create_files
- 🛑 仅 1 次机会，仍失败 → 返回 false

### 🛑 跳过规则（铁律）

| 条件 | 动作 |
|------|------|
| **写模式 + testScenarios 完整** | **跳过 Step 1**，直接 create_files |
| **修模式 + ban 明确** | **跳过搜集**，直接 read_files → edit_batch |
| create_files / edit_batch 成功 | 任务完成，输出 `<!--FINAL-->` |
| 失败 | 1 次修复机会，仍失败返回 false |

### 死循环防护

- create_files / edit_batch 连续失败 2 次 → 返回 false，结束
- 已输出 `<!--FINAL-->` → **立即停止**，不要再调任何工具

## 🛑 mock/real 双模式与第三方服务

逻辑层测试可以调用真实后端（supertest）或直调 service 函数（jest.mock DB），**但第三方服务在测试环境只能走 mock 模式**：

```
生产环境: PAYMENT_MODE=real → realCreatePayment() → 调用微信支付 API（需要密钥）
测试环境: PAYMENT_MODE=mock → mockCreatePayment() → 返回 mockHint 假数据（不需要密钥）
```

**测试策略：**

| 模式 | 能测吗 | 测什么 |
|------|:---:|------|
| mock | ✅ 完全可测 | HTTP 响应状态码、mockHint 字段存在、业务流程完整走通 |
| real | ⚠️ 结构可测 | 验证 real 函数存在、用 `process.env` 读密钥（不能测真实 API 调用） |

**断言规则：**

```javascript
// mock 模式下得正常响应
const res = await request(app).post('/api/orders').send({...});
expect(res.status).toBe(201);
// mock 模式返回 mockHint，不是错误
if (res.body.data.mockHint) {
  expect(res.body.data.mockHint).toContain('模拟');  // mock 标记存在
}
// 关键业务字段仍然正确
expect(res.body.data.orderId).toEqual(expect.any(Number));
```

🛑 **不要因为响应中有 `mockHint` 就判定测试失败**——这是 mock 模式的正常行为。
🛑 **不要尝试在测试中调真实第三方 API**——测试环境没有密钥，会直接报错。
🛑 **real 路径的验证**：源码中存在 `process.env.WECHAT_PAY_*` 引用 = 已正确实现，不需要运行时验证。

## 通用规则（所有逻辑子层适用）

- 测试文件名: `test/{task_id}.test.js`
- 断言值从真理 JSON 取，场景只定方向
- 步骤间变量传递：从上一步 `res.body.data` 提取，传给下一步
- 断言用 `toBe` / `toEqual` / `toContain`，不用正则

🛑 backend_proc 特有规则（mock DB/事务/affectedRows）在模板 [templates/logic/backend_proc.md](../../../templates/logic/backend_proc.md) 中。

## 子层文件

| 文件 | 适用范围 | 测试方式 |
|------|---------|---------|
| [backend_proc.md](logic/backend_proc.md) | 单接口内处理链（1 事务） | jest.mock DB → require service 函数直调 |
| [logic.md](logic/logic.md) | 跨功能数据流（≥2 事务） | supertest HTTP 串联 |
| [scenario.md](logic/scenario.md) | 全链路 ≥4 步 | supertest 长链 |

nfr 已移至 [quality.md](../quality.md)。

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/logic/](../../repair/a/logic/) 对应层级的修复策略。

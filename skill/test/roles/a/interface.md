# A: 接口层 — 通用规则

适用于: api / navigation / auth / db_api。**各子层的字段解读、测试点、独有规则在对应 `.md` 文件**。

## 通用流程

1. 读「任务数据（完整字段）」JSON → 了解 `sourceTask` / `_trace` / `dependencies`
2. 🆕 读 `## 🛑 下层真理`（如果有）→ 真理列出了上游已验证的**真实字段名/表名/函数签名**
3. 读「测试场景（验证集）」→ 场景给方向（测什么、什么 category），**不做精确值来源**
4. 对照「测试模板」写代码 → 断言中的精确值**从真理 JSON 中取**，场景只提供方向和 category
5. 调 `create_files` 一次写完

🛑 **场景 vs 真理的分工**：
- 场景的 `scenario` 名 → 确定测什么（方向）
- 场景的 `category` → 确定启用哪些验证维度
- 场景的 `output` 字段值 → **示例/参考，不作为精确断言值**
- 🛑 精确值（handler名、路径、错误码、列名）**只从真理取**，不从场景取
- 🛑 如果真理写 `addToCart` 而场景写 `add`，用真理的 `addToCart`——场景是简写

🛑 写模式不需要 read_files —— 测试代码用 `fs.readFileSync` / `require` 在**运行时**读源文件。

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
  {"file": "test/t_api_auth_register.test.js", "edits": [
    {"start": 47, "end": 46, "content": "  expect(res.status).toBe(401);"}
  ]},
  {"file": "test/t_api_auth_register.test.js", "edits": [
    {"start": 30, "end": 32, "content": "it('should reject expired token', async () => {\n  const res = await request(app).get('/api/users/me').set('Authorization', 'Bearer expired_token');\n  expect(res.status).toBe(401);\n});"}
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
  {"path": "test/t_api_auth_register.test.js", "content": "const request = require('supertest');\n...完整代码..."}
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
- 🛑 testScenarios 已包含全部信息，模板提供代码骨架
- 🛑 一次传完所有文件

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

## 🛑 mock/real 双模式识别

部分服务（支付/短信/OSS/微信登录）用 `*_MODE` 环境变量做 mock/real 切换：

```javascript
const PAYMENT_MODE = process.env.PAYMENT_MODE || 'mock';
async function createPayment(order) {
  if (PAYMENT_MODE === 'mock') {
    return { mockHint: '模拟支付，回调已自动处理', ... };
  }
  return realCreatePayment(order);  // 调用微信/支付宝 API
}
```

**这是合法的双路径模式，不是"缺代码"。** 测试时需要理解：

| 检查项 | 怎么测 |
|--------|--------|
| `*_MODE` 开关存在 | `src.includes('_MODE')` — 确认有模式切换 |
| mock 路径返回 mockHint | 源码中 `includes('mockHint')` |
| real 路径用 `process.env` 引用密钥 | 源码中 `includes('process.env.WECHAT_PAY')` 等，**禁止硬编码密钥** |
| real 路径不能只有注释 | 源码中 real 函数体不只是注释，有实际 API 调用代码 |

🛑 **误判陷阱**：源码只有 mock 路径、real 路径被注释掉 → 这是缺陷（`MISSING_REAL_PATH`）。源码 mock 和 real 都有完整实现 → 这是正确模式。

## 通用规则

- 测试文件名: `test/{task_id}.test.js`
- correct + error 两个 category 必有
- 断言用 `toContain` / `includes`，不用正则
- 各模板的「真理字段解读」表说明了字段含义，对照读 JSON 取值

## 子层文件

| 文件 | 适用范围 |
|------|---------|
| [api.md](api.md) | HTTP 请求响应对齐 — supertest 调后端接口 |
| [navigation.md](navigation.md) | 页面跳转 — fs.readFileSync 验证 router.push 参数传递 |
| [auth.md](auth.md) | Token + 中间件 — jwt.sign/verify 直调 + 静态检查 |
| [db_api.md](db_api.md) | SQL 列名 DDL 对照 — fs.readFileSync 验证列存在性 |

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/interface/](../../repair/a/interface/) 对应层级的修复策略。

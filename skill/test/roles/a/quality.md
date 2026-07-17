# A: 质量层 — 通用规则

适用于: nfr。质量层独立于逻辑层。安全用 jest+supertest，性能用 k6/autocannon。

## 通用流程

1. 读「任务数据（完整字段）」JSON → 了解 `sourceTask` / `dependencies`
2. 🆕 读 `## 🛑 下层真理`（如果有）→ 真理中有上游已验证的安全配置
3. 读「测试场景（验证集）」→ 每个 scenario 含 `input`(攻击载荷) / `output`(期望行为)
4. 对照测试模板写代码——断言值从真理 JSON 取，场景给方向
5. 调 `create_files` 一次写完

🛑 攻击载荷被拦截 = correct（正确行为），不是 error。
🛑 安全测试验证"不崩溃"（status !== 500），不验证精确 status。
🛑 并发测试 jest 单线程只能测 2 并发——真实压测用 k6/autocannon。

## 🛑 工具调用规则

### 可用工具

| 工具 | 参数 | 模式 | 限次 | 说明 |
|------|------|:---:|:---:|------|
| **create_files** | `files` | 写+修 | 2 次 | 写/修测试代码，自带语法检查 |
| **edit_batch** | `files` | 仅修 | 不限 | 定点修改测试文件，自带语法检查 |
| **read_files** | 无 | 仅修 | 不限 | 读取测试文件（不含源码） |
| **search_rag** | `query` | 写+修 | 1 次 | 可选。查历史经验 |
| **search_code** | `query` | 写+修 | 1 次 | 可选。查参考实现 |
| **install** | `packages` | 写+修 | 不限 | 缺 npm 包时用 |

🛑 模式判断：test 文件不存在 → **写模式**；test 文件已存在 + B 的 ban → **修模式**。

### 🛑 edit_batch 详解（仅修模式可用）

一次调用修改多个文件，每个文件可有多处编辑。行号 1-indexed。

```json
edit_batch(files=[
  {"file": "test/t_nfr_ratelimit.test.js", "edits": [
    {"start": 47, "end": 46, "content": "  expect(res.status).toBe(429);"}
  ]},
  {"file": "test/t_nfr_ratelimit.test.js", "edits": [
    {"start": 20, "end": 22, "content": "it('should block SQL injection', async () => {\n  const res = await request(app).post('/api/users/login').send({ username: \"' OR 1=1 --\", password: 'test' });\n  expect(res.status).not.toBe(500);\n});"}
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
  {"path": "test/t_nfr_ratelimit.test.js", "content": "const request = require('supertest');\n...完整代码..."}
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

**写模式 — Step 1: 搜集（可选）**
- 🛑 此步禁止 create_files
- 搜索失败/空结果 → 正常，不重试

**写模式 — Step 2: 写测试代码（必须）**
- 工具: `create_files`，**第一轮直接调，禁止先搜索再创建**
- 🛑 testScenarios 已包含攻击载荷和期望行为，模板提供完整骨架
- 🛑 一次传完所有文件

**写模式 — Step 3: 失败重写（1 次机会）**
- `WRITE REJECTED` / `files 格式错误` → 修正后重调 create_files
- 🛑 仅 1 次重写机会，仍失败 → 返回 false

---

**修模式 — Step 1: 读取（必须）**
- 工具: `read_files()` — **无参数**，只读测试文件（不含源码）
- 🛑 必须先读再改，不能盲改

**修模式 — Step 2: 修复（必须）**
- 工具: `edit_batch`（定点改）**或** `create_files`（重写）
- 🛑 B 的 ban 已含文件:行号 + fix 指令，直接改

### 🛑 跳过规则（铁律）

| 条件 | 动作 |
|------|------|
| **写模式 + testScenarios 完整** | **跳过搜索**，直接 create_files |
| **修模式 + ban 明确** | **跳过搜索**，直接 read_files → edit_batch |
| create_files / edit_batch 成功 | 任务完成，输出 `<!--FINAL-->` |
| 失败 | 1 次修复机会，仍失败返回 false |

### 死循环防护

- create_files / edit_batch 连续失败 2 次 → 返回 false，结束
- search_rag 或 search_code 各 > 1 次 → 框架直接拒绝
- 已输出 `<!--FINAL-->` → **立即停止**，不要再调任何工具

## 通用规则

- 测试文件名: `test/{task_id}.test.js`
- 安全测试: 发送攻击载荷 → 期望 `not.toBe(500)`
- SQL 注入: `'; DROP TABLE--`、`OR 1=1`、`UNION SELECT`
- XSS: `<script>`、`<img onerror>`、`<svg onload>`
- CORS: 非白名单 Origin → 被拒
- Token: jwt.sign 错误 secret → 401
- RateLimit: ≥50 并发 → 有 429
- 并发: `Promise.all([order(), order()])` → 1 成功 1 失败

## 子层文件

| 文件 | 适用范围 |
|------|---------|
| [nfr.md](quality/nfr.md) | 安全+性能测试 |

## 自我修复

B 判定 `fix_target=test` → 加载 [repair/a/quality/](../../repair/a/quality/) 对应层级的修复策略。

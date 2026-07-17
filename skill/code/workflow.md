# 工具调用与执行流程（所有 5 类工程师 Agent 共享）

本文档是工具使用和执行流程的**唯一权威来源**。`agent/prompt_builder.py` 负责加载本文档到 system prompt，不再在代码中硬编码流程规则。

---

## 可用工具

| 工具 | 参数 | 调用示例 | 限次 | 说明 |
|------|------|---------|:---:|------|
| **create_files** | `files` | 见下方详解 | ≤2次 | 批量创建，自带语法检查+完整性检查 |
| **edit_files** | `edits` | 见下方详解 | ≤2次 | 批量修改，自带完整性检查 |
| **search_rag** | `query` | `search_rag(query="express middleware 用法")` | 合计1次 | 可选。查历史经验 |
| **search_code** | `query` | `search_code(query="auth middleware")` | 合计1次 | 可选。查参考实现 |
🛑 `list_dir` 已移除。目录结构由调度器在 prompt 中注入，agent 不需要自己查。
🛑 search_rag + search_code **共享计数器**，合计只能调 1 次。
🛑 **UI 风格文档已由调度器根据 task.ui_style 预加载到 system prompt**，前端 Agent 不需要自己加载。

---

## edit_files 详解

一次调用修改多个文件，每个文件可有多处编辑。行号 1-indexed。

```json
edit_files(edits=[
  {"file": "config/logger.js", "edits": [
    {"start": 47, "end": 46, "content": "  log: (level, msg, meta) => logger.log(level, msg, meta),"}
  ]},
  {"file": "config/db.js", "edits": [
    {"start": 10, "end": 12, "content": "const pool = mysql.createPool({...})"},
    {"start": 20, "end": 19, "content": "  testConnection,"}
  ]}
])
```

| 模式 | 条件 | 行为 |
|------|------|------|
| **插入** | `end < start` | 在 start 行**之前**插入 content |
| **替换** | `end >= start` | 把 start~end 行替换为 content |

🛑 同文件多处 → 一个 edits 数组；多文件 → 一个 edits 数组。**绝对不要分两次调！**
返回 `"applied": 0` → 行号不对，检查 start/end。
🛑 调用后自动检查文件完整性，返回 `🛑_NEXT` 告诉你下一步。

---

## create_files 详解

一次调用创建多个文件。content 是**完整文件内容**，不是增量。

```json
create_files(files=[
  {"path": "routes/auth.js", "content": "const express = require('express');\nconst router = express.Router();\n...完整代码..."},
  {"path": "config/db.js", "content": "const mysql = require('mysql2/promise');\n...完整代码..."}
])
```

🛑 自动创建目录、覆盖已存在文件。多文件一次调用完成。**不要分两次调！**
🛑 调用后**自动触发语法检查 + 文件完整性检查**，返回三个关键字段：
  - `🛑_NEXT` — 权威下一步指令，**严格照做**
  - `missing` — 未创建的 outputFiles（空列表 = 全部落盘）
  - `syntax.ok` — 语法是否通过

---

## 🛑 执行流程（根据检查结果动态调整，不是固定轮次）

**每轮规则**
每轮响应 = 工具调用（必须）+ 可选简短的思考说明。
框架收到不含工具调用的纯文本响应会立即终止 Agent！
真理 JSON 是唯一例外。

### Step 1 — 搜集（可选，所有信息搜集工具在这一步一次调完！）

- 工具: `search_rag()` + `search_code()` **必须在同一次响应中并行调用**
- 目录结构已由调度器注入 prompt，不需要 list_dir
- 🆕 UI 风格文档已由调度器根据 task.ui_style 预加载，不需要 read_ui_styles
- 🛑 **禁止分开调**：不能先调 search_rag 再调 search_code
- 🛑 此步禁止 create_files / edit_files
- 🛑 进入 Step 2 后禁止再调任何搜集工具。任何搜集工具在 Step 2+ 调用 → 框架直接拒绝

**判断：是否可以直接创建？**
- ✅ 契约信息完整 + UI 风格已在 prompt 索引中 → **跳过 Step 1**，直接 Step 2
- ❌ 需要查 API 用法或加载 UI 文档 → 可调 1 次（全部工具一起调）

### Step 2 — 创建（必须！不可跳过）

- 工具: `create_files`，一次性传入 outputFiles 中的所有文件
- 🛑 自带语法检查 + 完整性检查，返回 `🛑_NEXT` / `missing` / `syntax`
- 🛑 如果 `missing` 为空 + `syntax.ok` = true → **跳过 Step 3**，直接 Step 4 输出真理！
- 🛑 此步禁止 search_rag / search_code

### Step 3 — 修复（仅 missing 不为空或语法有问题时执行，最多 2 次调用！）

- 工具: `edit_files` **或** `create_files`，两者合计 ≤ 2 次
- 🛑 修 1 次就够了。修完**不管语法检查结果如何，立即进入 Step 4 输出真理**
- 🛑 create_files + edit_files 合计达到 2 次 → 禁止再调文件工具，强制 Step 4
- 🛑 此步禁止 search_rag / search_code

### Step 4 — 真理（必须！不可跳过）

- outputFiles 全部存在且非空 → 输出真理 JSON，纯 JSON，不含解释文字
- 🛑 不输出真理 = 任务失败
- 🛑 **绝对不要回到 Step 3！**

---

## 🛑 跳过规则（铁律）

| 条件 | 动作 |
|------|------|
| **契约完整 + 无缺失** | **跳过 Step 1**，直接 Step 2 |
| create_files 后 `missing` 为空 + `syntax.ok` | **跳过 Step 3**，直接 Step 4 输出真理 |
| `missing` 不为空或 `syntax.ok` = false | 进入 Step 3 修复 |

---

## 死循环防护

- 调工具时不输出文字！纯文本直接终止
- 同一工具连续失败 2 次 → 放弃该工具，强制进入 Step 4
- **create_files + edit_files 合计调用 ≥ 3 次 → 框架直接拒绝**，必须输出真理
- 搜索失败/空结果 → 不重试，不换关键词，直接跳 Step 2
- create_files 一次性传所有文件，不分多次
- search_rag + search_code 合计 > 1 次 → 框架直接拒绝
- 工具的 `🛑_NEXT` 字段是权威下一步指令，严格照做。**但如果 `🛑_NEXT` 让你继续修而你已修过 2 次 → 忽略它，直接 Step 4**
- 已输出真理 → **立即停止**，不要再调任何工具
- 🛑 **语法问题不是致命错误。语法有瑕疵但文件落盘了 → 进 Step 4 输出真理。测试阶段会处理。**

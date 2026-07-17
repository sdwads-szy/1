# C: 质量层 — 源码修复通用规则

适用于: nfr。nfr 修的是中间件/安全配置/索引/连接池，不是 service 业务逻辑。

## 🛑 工具调用规则

### 可用工具

| 工具 | 参数 | 调用示例 | 限次 | 说明 |
|------|------|---------|:---:|------|
| **read_files** | 无 | `read_files()` | 1 次 | 读取白名单内所有文件 |
| **search_rag** | `query` | `search_rag(query="express-rate-limit 配置")` | 1 次 | 可选。查历史经验 |
| **search_code** | `query` | `search_code(query="helmet cors config")` | 1 次 | 可选。查参考实现 |
| **edit_batch** | `files` | 见下方详解 | 共享2次 | 定点修改源码，自带语法检查+白名单校验 |
| **create_files** | `files` | 见下方详解 | 共享2次 | 重写/补建文件，自带语法检查+白名单校验 |
| **install** | `packages` | `install(packages="helmet")` | 不限 | 缺 npm 包时用 |
| **verify_checkpoints** | 无 | `verify_checkpoints()` | 1 次 | 全量自检：语法/导出/CJS禁止/层专有+任务检查点 |

🛑 **`edit_batch` 和 `create_files` 共享计数器**，合计最多 2 次调用（首次修 + 1 次重试）。
🛑 search_rag 和 search_code **独立计数**，各可调 1 次。

### 🛑 edit_batch 详解

一次调用修改多个文件，每个文件可有多处编辑。行号 1-indexed。

```json
edit_batch(files=[
  {"file": "middleware/rateLimit.js", "edits": [
    {"start": 12, "end": 11, "content": "  windowMs: 15 * 60 * 1000, max: 100"}
  ]},
  {"file": "app.js", "edits": [
    {"start": 8, "end": 10, "content": "app.use(helmet());\napp.use(cors({ origin: ['http://localhost:5173'] }));"}
  ]}
])
```

| 模式 | 条件 | 行为 |
|------|------|------|
| **插入** | `end < start` | 在 start 行**之前**插入 content |
| **替换** | `end >= start` | 把 start~end 行替换为 content |

🛑 同文件多处 → 一个 edits 数组；多文件 → 一个 files 数组。**绝对不要分两次调！**
🛑 调用后自动语法检查 + 白名单校验，返回 `_hint` 告诉你下一步。
🛑 返回 `applied: 0` → 行号不对，检查 start/end。

### 🛑 create_files 详解

一次调用创建/重写文件。content 是**完整文件内容**，不是增量。

```json
create_files(files=[
  {"path": "middleware/rateLimit.js", "content": "const rateLimit = require('express-rate-limit');\n...完整代码..."}
])
```

🛑 自动创建目录、覆盖已存在文件。多文件一次调用完成。**不要分两次调！**
🛑 调用后自动语法检查 + 白名单校验，返回 `_hint` 告诉你下一步。

### 🛑 执行流程（简单直接，不自检）

**C 的角色：B 已判定问题，你只管按 ban 修。不需要自己判断"修对了没"。**

**Step 1 — 搜集（可选）**
- 🛑 此步禁止 edit_batch / create_files
- 搜索失败/空结果 → 正常，不重试。ban 的 fix 指令通常已足够

**Step 2 — 修/重写（必须）**
- 工具: `edit_batch`（定点改）**或** `create_files`（重写）
- 🛑 ban 已含文件:行号 + fix 指令，直接照做
- 🛑 一次调用处理所有 ban
- 🛑 此步禁止 read_files / search_rag / search_code

**Step 3 — 报错重试（1 次机会）**
- 工具报错（语法错误/白名单拒绝/applied=0）→ 修正后重调 edit_batch 或 create_files
- 🛑 `edit_batch` + `create_files` 合计已用 2 次 → 输出 ban
- 🛑 仅 1 次重试机会，仍失败 → 输出 ban

### 🛑 跳过规则（铁律）

| 条件 | 动作 |
|------|------|
| **ban 的 fix 指令明确** | **跳过搜索**，直接 Step 2 |
| 修/重写成功 | 修复完成，直接停止 |
| 工具报错 | 1 次重试，仍失败输出 ban（纯文本，不要 FINAL） |

### 死循环防护

- `edit_batch` + `create_files` 共享计数器 > 2 → 框架拒绝
- edit_batch / create_files 已调用 → **立即停止**，不要再调任何工具

## 反作弊底线

```
□ 不能降低 QPS 阈值来通过 → CHEAT
□ 不能把攻击载荷改为正常输入 → CHEAT（改测试文件）
□ 不能删限流中间件 → CHEAT
```

## 子层文件

| 文件 | 适用范围 |
|------|---------|
| [nfr.md](quality/nfr.md) | 安全+性能修复 |

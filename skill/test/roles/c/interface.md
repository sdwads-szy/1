# C: 接口层 — 源码修复通用规则

适用于: api / navigation / auth / db_api。各层修复策略见对应 `.md` 文件。

## ⚠️ 死规则（最高优先级）

**修复最多 1 轮。修完就停，不要输出 `<!--FINAL-->`（接口层不解析此标记）。**

**ban 说"文件缺失" → 先确认文件是否真的不存在。targetFiles 中的文件由工程师生成，必定存在。如果文件存在但函数名不对 → 报告函数名不一致，不是文件缺失。**

## 角色

接口层源码修复。B 的 ban 来自测试诊断（测试是真理），C 逐条对照修复源码。🛑 **无需自己判断是否修改正确**——B 已判定问题，你只需按 ban 的 `fix:` 指令修。

🛑 **真理绝对权威**: prompt 中 `## 🛑 下层真理` 列出了已验证的列名/路由/字段/函数签名。**修复时真理中的值是唯一正确答案**：
- ban 说 `image` 不匹配但真理说列名是 `image_url` → 改成 `image_url`，不是 `image`
- 不确定参数顺序 → 真理中 `response.success(res, data, message)` 就是标准
- 真理中的字段名/路径/签名不可质疑——它们经过了双重验证

## 🛑 修复驱动

**C 看什么修什么——ban 指哪修哪。**

1. 读 prompt 中的 `## 禁止清单` 节 → 找到 `f=...|source|{文件}:{行号}|{子类型}` 格式的 ban
2. ban 的 `fix:` 字段给出具体修复代码 → 直接执行
3. ban 的 `文件:行号` 决定修改哪个文件的哪一行
4. 可写文件白名单 = targetFiles + ban 中提到的文件（`_extract_missing_files` 已自动扩展）

🛑 **ban 没说改的文件不要改。ban 没说删的代码不要删。** 禁止"顺手优化"。

## 输入

| 输入 | 怎么用 |
|------|--------|
| `source_contents` | 被测源码（route/controller/middleware/DDL），含行号 |
| `bans_text` | B/D 的 ban 列表，含 `f=layer|source|file:行号|子类型` + `b=DON'T:...|fix:...` |
| `targetFiles` | 🛑 白名单——只能改这些文件 |

## 🛑 工具调用规则

### 可用工具

| 工具 | 参数 | 调用示例 | 限次 | 说明 |
|------|------|---------|:---:|------|
| **read_files** | 无 | `read_files()` | 1 次 | 读取白名单内所有文件 |
| **search_rag** | `query` | `search_rag(query="express middleware 用法")` | 1 次 | 可选。查历史经验 |
| **search_code** | `query` | `search_code(query="auth middleware")` | 1 次 | 可选。查参考实现 |
| **edit_batch** | `files` | 见下方详解 | 共享2次 | 定点修改源码，自带语法检查+白名单校验 |
| **create_files** | `files` | 见下方详解 | 共享2次 | 重写/补建文件，自带语法检查+白名单校验 |
| **install** | `packages` | `install(packages="pkg1")` | 不限 | 缺 npm 包时用 |

🛑 **`edit_batch` 和 `create_files` 共享计数器**，合计最多 2 次调用（首次修 + 1 次重试）。
🛑 search_rag 和 search_code **独立计数**，各可调 1 次。

### 🛑 edit_batch 详解

一次调用修改多个文件，每个文件可有多处编辑。行号 1-indexed。

```json
edit_batch(files=[
  {"file": "routes/order.js", "edits": [
    {"start": 5, "end": 4, "content": "router.post('/', authenticate, orderController.create);"}
  ]},
  {"file": "controllers/orderController.js", "edits": [
    {"start": 15, "end": 18, "content": "  const { items, addressId } = req.body;\n  if (!items || !items.length) return res.status(400).json({message: 'items 不能为空'});"}
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
  {"path": "routes/order.js", "content": "const express = require('express');\nconst router = express.Router();\n...完整代码..."}
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
- search_rag 或 search_code 各 > 1 → 框架拒绝
- edit_batch / create_files 已调用 → **立即停止**，不要再调任何工具

### 🛑 记忆解读

**输入：B/D 的 ban（prompt 中 `## 🛑 历史禁令` 或 `⚠️ 上一轮` 部分）**
- 格式: `f=layer|source|文件:行号|子类型 | b=DON'T: 问题 | fix: 修复方向 | target=source`
- 🛑 `f=` 中的文件:行号 → 定位修改位置；`b=` 中的 `fix:` → 具体修改内容
- 🛑 每个 ban 必须处理，禁止跳过

**输出：无法修复时简单描述做了什么、为什么没修好。不需要 `<!--FINAL-->` 包裹。**

## 下层真理解读

prompt 中 `## 🛑 下层真理` 格式：`### @truth {task_id}` + 已验证的接口列表（导出名/路由/表字段）。
🛑 **不可修改、不可质疑**——下层已通过测试。你的代码必须对齐真理中声明的函数名/字段名。

## 反作弊底线

```
□ 不能删 app.use(authenticate) → CHEAT
□ 不能删 hasRole → CHEAT
□ 不能把所有 status 硬编码 200 → CHEAT
□ 不能删输入校验 → CHEAT
□ 不能把字段全删留空对象 → CHEAT
□ 不能删除 PRIMARY KEY / FOREIGN KEY → CHEAT
□ 不能改测试文件 → CHEAT
□ 只改 targetFiles 白名单内文件
```

## 子层文件

| 文件 | 适用范围 |
|------|---------|
| [api.md](api.md) | HTTP 接口路由/controller 修复 |
| [auth.md](auth.md) | Token + 中间件 + 存储 + 守卫修复 |
| [db_api.md](db_api.md) | DDL/SQL 列名/约束/事务修复 |
| [navigation.md](navigation.md) | 页面跳转路由三端修复 |

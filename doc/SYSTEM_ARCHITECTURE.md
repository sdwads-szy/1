# Agent 多智能体代码生成系统 — 系统架构文档

> **版本**: v1.0  
> **日期**: 2026-06-29  
> **项目路径**: `<project_root>`

---

## 目录

1. [系统概述](#1-系统概述)
2. [技术栈](#2-技术栈)
3. [总体架构](#3-总体架构)
4. [主流水线（4 步）](#4-主流水线4-步)
5. [目录结构](#5-目录结构)
6. [模块详解](#6-模块详解)
   - [6.1 agent/ — 核心 Agent 实现](#61-agent--核心-agent-实现)
   - [6.2 brainAgent/ — 编排调度器](#62-brainagent--编排调度器)
   - [6.3 localAgent/ — LLM 调用封装](#63-localagent--llm-调用封装)
   - [6.4 utils/ — 共享工具](#64-utils--共享工具)
   - [6.5 Tools/ — 可复用工具](#65-tools--可复用工具)
   - [6.6 skill/ — Agent 技能文档](#66-skill--agent-技能文档)
   - [6.7 config/ — 配置文件](#67-config--配置文件)
7. [数据流](#7-数据流)
8. [依赖图与分层架构](#8-依赖图与分层架构)
9. [RAG 知识库子系统](#9-rag-知识库子系统)
10. [测试验证子系统（ABCD 循环）](#10-测试验证子系统abcd-循环)
11. [运行时数据与存储](#11-运行时数据与存储)
12. [接口真理（Truth）系统](#12-接口真理truth系统)
13. [评分系统](#13-评分系统)
14. [外部依赖](#14-外部依赖)
15. [关键设计模式](#15-关键设计模式)
16. [错误处理与容错](#16-错误处理与容错)

---

## 1. 系统概述

本系统是一个**多智能体 AI 代码生成引擎**，能够从一句自然语言需求描述，全自动生成一套完整的 Web 应用（Node.js + Express + MySQL 后端，Vue 3 + Vite + Pinia 前端），并包含自动化测试、修复和多轮迭代优化。

### 核心能力

- **需求分析**：多角色（客户、用户、产品经理、架构师、安全专家等）多轮讨论，输出完整 PRD
- **架构设计**：从 PRD 自动生成 7 类契约（Scenario/Model/Logic/API/DB-API/Navigation/Auth）+ 5 类开发任务（Infra/DB/Backend/Frontend/Integration）
- **代码生成**：按严格类型分层并发执行，LLM 缓存友好，支持依赖剪枝
- **测试验证**：13 层 ABCD 循环（A写测试 → B运行诊断 → C修复源码 → D验证修复），多轮自动修复
- **知识库（RAG）**：从测试/源码失败的记忆中提炼经验，向量化存储，检索辅助后续任务
- **代码评分**：5 维度自动评分（S/A/B/C/D），高分代码自动入库

### 目标产物

```
work/project/
  ├── app.js                    # Express 入口
  ├── package.json              # npm 配置
  ├── .env                      # 环境变量
  ├── middleware/               # 认证/权限/错误处理
  ├── config/db.js              # MySQL 连接池
  ├── routes/                   # Express 路由
  ├── services/                 # 业务逻辑层
  ├── database/schema_*.sql     # DDL 脚本
  ├── src/                      # Vue 3 前端
  │   ├── pages/                # 页面组件
  │   ├── components/           # 通用组件
  │   ├── stores/               # Pinia 状态管理
  │   ├── api/                  # Axios API 封装
  │   └── router/index.js       # Vue Router
  ├── scripts/init-db.js        # 数据库初始化
  └── test/                     # Jest/Vitest 测试
      ├── unit/
      ├── business/
      ├── joint/
      └── special/
```

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **LLM** | DeepSeek V4 Pro (via OpenAI-compatible API) | 主要推理模型 |
| **Agent 框架** | `picoagents` | Agent 创建、流处理、工具调度 |
| **后端目标** | Node.js + Express + MySQL | 生成代码的运行环境 |
| **前端目标** | Vue 3 + Vite + Pinia + Axios | 生成代码的运行环境 |
| **测试** | Jest / Vitest | 自动化测试框架 |
| **向量数据库** | LanceDB | RAG 知识库存储 |
| **嵌入模型** | Qwen3-Embedding-4B | 文本向量化 |
| **重排序** | Qwen3-Reranker-4B | 检索结果重排 |
| **缓存** | Redis (可选，降级为文件) | 测试快照缓存、RAG 查询缓存 |
| **本地模型** | Qwopus3.5-4B-coder (llama-server) | 可选的本地推理 |
| **语言** | Python 3 | 系统实现语言 |

---

## 3. 总体架构

```
                          ┌─────────────────────────────────────┐
                          │         用户 (一句话需求)             │
                          └─────────────────┬───────────────────┘
                                            │
                          ┌─────────────────▼───────────────────┐
                          │      brainAgent/basic.py             │
                          │         (统一入口)                    │
                          └─────────────────┬───────────────────┘
                                            │
          ┌─────────────────────────────────┼─────────────────────────────────┐
          │                                 │                                 │
  ┌───────▼────────┐  ┌────────────▼──────┐  ┌───────────▼────────┐  ┌───────▼────────┐
  │ Step 1          │  │ Step 2            │  │ Step 3              │  │ Step 4          │
  │ 需求分析         │  │ 架构设计           │  │ 代码生成             │  │ 测试验证         │
  │ orchestrator.py │  │ architect.py      │  │ engineer.py         │  │ scheduler.py    │
  │ → PRD 报告       │  │ → task.json       │  │ → 源代码             │  │ → 测试通过/修复  │
  └───────┬────────┘  └────────────┬──────┘  └───────────┬────────┘  └───────┬────────┘
          │                        │                     │                    │
          │              ┌─────────┴─────────┐           │                    │
          │              │ 7 类契约           │           │                    │
          │              │ 5 类任务           │           │                    │
          │              └───────────────────┘           │                    │
          │                                              │                    │
          │                        ┌─────────────────────┴────────┐           │
          │                        │  RAG 检索 (search_rag)        │◄──────────┘
          │                        │  代码检索 (search_code)       │
          │                        │  记忆系统 (Memory/)          │
          │                        └──────────────────────────────┘
          │
          └──────────────────────────────────────────────────────────────────┘
```

---

## 4. 主流水线（4 步）

### Step 1: 需求分析

**入口**: `brainAgent/orchestrator.py → run_demand_analysis()`  
**核心 Agent**: `agent/product_manager.py`  
**输出**: `work/project/doc/requirement_report_*.md`

**流程**:
1. 初始化会话（`full_memory.json` + `full_summary.json`）
2. 前 N-1 轮：`discuss` 模式 — PM Agent 加载多个角色卡片（Customer, User, Manager, Innovator, Business, QA, Data, Architect, Security）进行多角度需求讨论
3. 最后一轮：`final_output` 模式 — 输出完整 PRD 文档
4. 如果 LLM 未产出有效 PRD，降级为从 `full_summary.json` 自动生成

**关键文件**:
- [agent/product_manager.py](agent/product_manager.py) — PM Agent 实现
- [brainAgent/orchestrator.py](brainAgent/orchestrator.py) — 需求分析编排器
- [Tools/memory/load_memory.py](Tools/memory/load_memory.py) — 记忆加载
- [Tools/memory/save_memory.py](Tools/memory/save_memory.py) — 记忆保存
- [Tools/memory/merge_memory.py](Tools/memory/merge_memory.py) — 摘要合并

### Step 2: 架构设计

**入口**: `agent/architect.py → run_architect_agent()`  
**输出**: `work/project/task/task_<timestamp>.json`

**生成的 7 类契约**:
| 契约类型 | 说明 |
|----------|------|
| `scenario` | 业务场景（用户故事 → 交互流程） |
| `model` | 数据模型（表结构、字段、约束） |
| `logic` | 业务逻辑（事务边界、并发控制、补偿逻辑） |
| `api` | API 接口（路由、端点、请求/响应） |
| `db-api` | 数据库 API（SQL 模板、参数、返回值） |
| `navigation` | 前端导航（页面跳转、数据传递） |
| `auth` | 认证授权（Token 配置、刷新策略） |

**生成的 5 类任务**:
| 任务类型 | 说明 | 优先级 |
|----------|------|--------|
| `infra` | 基础设施（中间件、工具、配置） | 0 |
| `db` | 数据库（DDL、初始化脚本） | 1 |
| `frontend` | 前端（Vue 3 页面、Store、API） | 1.5 |
| `backend` | 后端（Express 路由、Service） | 4.5 |
| `integration` | 集成（路由注入、环境变量、最终校验） | 99 |

**架构师后处理**:
- 依赖注入（从 `config/file_refs.json` 注入已知文件依赖）
- 外键检查（模型间外键关系验证）
- 导航依赖（前端页面跳转关系）
- 环境变量约束提取
- 第三方服务检测

### Step 3: 代码生成

**入口**: `brainAgent/engineer.py → run_engineer()`  
**输出**: 完整源代码 + `Memory/truths/engineer/*.json`

**执行流程**:
1. 加载 `task_*.json`，解析任务和契约
2. 契约关键字段校验（model 必须有 tableName，api 必须有 basePath）
3. 文件冲突检测
4. 依赖图构建 → `build_layered()` 严格类型分层
5. 分离 integration 任务
6. 逐层并发执行（同层内并发，层间串行，支持依赖剪枝）
7. 执行 integration 任务（路由注入、require 修复、env 补全）
8. 语法检查（`node --check`）+ 环境变量一致性检查
9. 生成执行报告 `execution_report_*.json`

**5 类 Agent 的调度**:

```
Layer 0: [infra]        ── 同层并发
    ├── middleware/auth.js
    ├── middleware/permission.js
    ├── utils/response.js
    ├── config/db.js
    └── .env + .env.example

Layer 1: [db]           ── 同层并发
    ├── database/schema_*.sql
    └── scripts/init-db.js

Layer 2: [frontend]     ── 同层并发（先生成，产出前端真理）
    ├── src/pages/Login.vue
    ├── src/stores/user.js
    ├── src/api/auth.js
    └── src/router/index.js

Layer 3: [backend]      ── 同层并发（接收前端真理 + DB 模型）
    ├── routes/auth.js
    ├── services/userService.js
    └── ...

Layer 4: [integration]  ── 单独执行
    └── app.js 路由注入 + src/main.js + .env 补全
```

**依赖剪枝算法**: 节点失败 → 沿依赖链向下递归裁剪全部后代节点。根因修复后自动解除。

### Step 4: 测试验证

**入口**: `brainAgent/scheduler.py → run_scheduler()`  
**输出**: 测试通过/失败报告 + 自动修复 + 评分

详见 [第 10 节](#10-测试验证子系统abcd-循环)。

---

## 5. 目录结构

```
Agent/
├── .claude/                    # Claude CLI 配置
│   └── settings.local.json     # 权限/允许的命令
├── .env.example                # 环境变量模板
├── agent/                      # ── 核心 Agent 实现 (13 文件) ──
│   ├── base_designer.py        #   设计器基类（infra/db/backend/frontend 共用）
│   ├── backend_designer.py     #   后端设计器（薄封装 → BaseDesigner）
│   ├── frontend_designer.py    #   前端设计器（薄封装 → BaseDesigner）
│   ├── database_designer.py    #   数据库设计器（扩展 BaseDesigner，SQL 专项）
│   ├── infrastructure_designer.py # 基础设施设计器（.env 一致性检查）
│   ├── integrator.py           #   集成 Agent（路由注入/require 修复）
│   ├── product_manager.py      #   产品经理 Agent（多轮需求讨论）
│   ├── architect.py            #   架构师 Agent（PRD → 契约 + 任务）
│   ├── prompt_builder.py       #   统一提示词组装器
│   ├── test_architect.py       #   测试架构师 Agent
│   ├── test_writer.py          #   测试编写 Agent（Step A）
│   ├── test_runner.py          #   测试诊断 Agent（Step B + D）
│   └── source_fixer.py         #   源码修复 Agent（Step C）
├── brainAgent/                 # ── 编排调度器 (6 文件) ──
│   ├── basic.py                #   统一入口（CLI 参数控制起止阶段）
│   ├── orchestrator.py         #   需求分析编排器
│   ├── engineer.py             #   工程调度器（分层并发 + 剪枝）
│   ├── scheduler.py            #   测试调度器（ABCD 循环 + Redis 快照）
│   ├── knowledge_builder.py    #   知识库构建器（6 步流水线）
│   └── retrieval_scheduler.py  #   统一检索调度器（3x3 扩散搜索）
├── localAgent/                 # ── LLM 调用封装 (2 文件) ──
│   ├── knowledge_builder.py    #   refine + merge LLM 调用
│   └── retrieval_agent.py      #   angle_analysis + deliver LLM 调用
├── config/                     # ── 配置文件 (4 文件) ──
│   ├── env_defaults.json       #   环境变量默认值
│   ├── file_refs.json          #   已知文件引用依赖映射
│   ├── infra_fixes.json        #   基础设施自动修复模式
│   └── mock_factories.json     #   Jest Mock 工厂策略（21 个包）
├── skill/                      # ── Agent 技能文档 (~80+ 文件) ──
│   ├── code/                   #   代码质量标准
│   │   ├── quality.md          #   代码质量 + 三端运行时规范
│   │   ├── readability.md      #   可读性规范
│   │   └── ui.md               #   前端 UI 设计规范
│   ├── design/                 #   PM 角色卡片 + PRD 模板
│   │   ├── product_manager.md  #   PM 主技能
│   │   ├── customer.md, user.md, manager.md, innovator.md
│   │   ├── business_expert.md, qa.md, data.md
│   │   ├── architect.md, security.md
│   │   └── prd_template.md
│   ├── engineer/               #   工程师角色定义
│   │   ├── architect.md, backend.md, frontend.md
│   │   ├── database.md, infrastructure.md, integrator.md
│   ├── test/                   #   测试规范 + 模板
│   │   ├── test_architect.md   #   测试架构设计
│   │   ├── a/                  #   写测试诊断 (11 文件)
│   │   ├── b/                  #   运行诊断 (11 文件)
│   │   ├── c/                  #   源码修复 (11 文件)
│   │   ├── d/                  #   验证诊断 (11 文件)
│   │   ├── roles/              #   各步角色定义
│   │   └── templates/          #   测试模板 (17 个)
│   └── rag/                    #   RAG 指令
│       ├── refine.md, merge.md
│       ├── angle_analysis.md, deliver.md
│       └── retrieval_skill.md
├── Tools/                      # ── 可复用工具 (20+ 文件) ──
│   ├── coding/                 #   文件 CRUD + 语法检查
│   │   ├── create_file.py      #   创建单个文件
│   │   ├── create_files.py     #   批量创建文件
│   │   ├── delete_file.py      #   删除文件
│   │   ├── edit_lines.py       #   按行编辑
│   │   ├── modify_file.py      #   修改文件
│   │   ├── read_file.py        #   读取文件
│   │   ├── list_files.py       #   列出目录
│   │   ├── get_functions_info.py # 提取函数信息
│   │   └── syntax_check.py     #   node --check 语法检查
│   ├── memory/                 #   记忆管理
│   │   ├── ban_memory.py       #   禁令记忆（指纹 + 禁令对）
│   │   ├── load_memory.py      #   JSON 记忆加载
│   │   ├── save_memory.py      #   JSON 记忆保存
│   │   └── merge_memory.py     #   摘要合并
│   ├── rag/                    #   RAG 知识库
│   │   ├── build/tools.py      #   表管理/嵌入/过滤/去重/锚点
│   │   ├── retrieval/tools.py  #   单角度检索/去重/统计
│   │   ├── code_retrieval/     #   代码检索（BM25 + 向量 + Reranker）
│   │   ├── search_rag.py       #   RAG 检索 Agent 工具
│   │   └── search_code.py      #   代码检索 Agent 工具
│   ├── contract/               #   契约处理
│   │   └── parser.py           #   契约 → 实现指令 / 测试场景
│   ├── scoring/                #   代码评分
│   │   └── code_scorer.py      #   5 维评分 + S/A/B/C/D 等级
│   ├── skill/                  #   技能加载
│   │   └── load_skill.py       #   加载 Markdown 技能文件
│   └── testing/                #   测试执行
│       └── run_test.py         #   Jest/Vitest 运行 + 结果解析
├── utils/                      # ── 共享工具 (4 文件) ──
│   ├── dependency_graph.py     #   依赖图构建（类型分层拓扑排序）
│   ├── json_extractor.py       #   LLM 输出 JSON 提取
│   ├── logger.py               #   统一日志（文件 + stderr）
│   └── token.py                #   Token 追踪（非侵入式流包装）
├── knowledge/                  # ── 运行时：LanceDB 向量数据库 ──
├── Memory/                     # ── 运行时：Agent 记忆 + 日志 ──
├── work/                       # ── 运行时：生成产物 ──
└── doc/                        # ── 文档 ──
    └── SYSTEM_ARCHITECTURE.md  #   本文档
```

---

## 6. 模块详解

### 6.1 agent/ — 核心 Agent 实现

#### 6.1.1 BaseDesigner (`agent/base_designer.py`)

**所有工程 Agent 的基类**，封装了以下公共逻辑：

- Agent 创建（`picoagents.Agent`，配置 tools、model_client、max_iterations）
- 流处理（`wrap_agent_stream` 包装，捕获 ErrorEvent / FatalErrorEvent）
- JSON 解析错误自动重试（非 db 类型）
- 工具列表组装（`create_files`、`edit_files`、`search_rag`、`search_code`）
- 对外接口提取（`_extract_exposed_interface` — LLM 精读源码 + 契约 + 依赖链）
- 真理文件搬运（workspace → 项目根 Memory/）
- 真理一致性交叉验证（Agent 声明 vs 正则扫描）

**子类**:
| 子类 | 文件 | 差异化 |
|------|------|--------|
| `BackendDesigner` | `backend_designer.py` | `agent_type="backend"` |
| `FrontendDesigner` | `frontend_designer.py` | `agent_type="frontend"` |
| `DatabaseDesigner` | `database_designer.py` | `agent_type="db"`, 禁用 JSON 重试，检查 SQL 文件 |
| `InfrastructureDesigner` | `infrastructure_designer.py` | `agent_type="infra"`, 注入 env 模板，env 一致性校验 |

**动态 max_iterations**: `base=3`，文件数>3 则+1，契约数>5 则+1，上限 5。integration 基础值为 4。

#### 6.1.2 Product Manager (`agent/product_manager.py`)

- 两种动作模式：`discuss`（轻量讨论）和 `final_output`（完整 PRD）
- 加载 9 个角色卡片（从 `skill/design/`）
- 多轮记忆管理（读写 `full_memory.json` / `full_summary.json`）
- `save_report` 工具：将最终 PRD 写入文件

#### 6.1.3 Architect (`agent/architect.py`)

- 读取 PRD 报告 → 生成 `task_<timestamp>.json`
- 7 类契约 + 5 类任务
- 大量后处理逻辑：
  - `_inject_dependencies()` — 从 `file_refs.json` 注入文件级依赖
  - `_inject_foreign_keys()` — 外键检查
  - `_inject_navigation_deps()` — 导航依赖
  - `_inject_env_constraints()` — 环境约束提取
  - `_third_party_detect()` — 第三方服务检测

#### 6.1.4 Test Architect (`agent/test_architect.py`)

- 读取 PRD + task.json → 生成 `test_tasks_<timestamp>.json`
- 8 层测试计划（repair/infra/db/frontend_static/auth/db_api/api/backend_proc/navigation/logic/scenario/nfr）
- LLM 输出分片合并支持
- 自动修复 targetFiles（验证源任务 outputFiles 存在性）

#### 6.1.5 Test Writer (`agent/test_writer.py`) — Step A

- 从测试任务生成 Jest/Vitest 测试文件
- 检测 ESM/CJS 模块格式
- 检测第三方库依赖以生成准确 Mock
- 语法验证 + Mock 完整性检查 + 闭包完整性检查
- 确定性 Mock 块生成（`app.js` + 冒烟测试）

#### 6.1.6 Test Runner (`agent/test_runner.py`) — Step B + D

- B 步骤：诊断测试失败，输出禁令（fingerprint → prohibition）
- D 步骤：验证源码修复
- 加载层次诊断角色（`skill/test/b/` / `skill/test/d/`）
- 从错误堆栈提取源码上下文
- 生成结构化真理输出

#### 6.1.7 Source Fixer (`agent/source_fixer.py`) — Step C

- 基于测试禁令修复源码
- 白名单写目标（只能修改 targetFiles 中的文件）
- 编辑后语法验证
- 支持用兄弟参考文件作为模板创建缺失文件

#### 6.1.8 Integrator (`agent/integrator.py`)

- 预扫描缺失的 require/import 路径
- 注入后端路由到 `app.js`
- 修复多导出路由模块
- 扫描缺失的环境变量
- 最终语法 + 环境一致性收尾

#### 6.1.9 Prompt Builder (`agent/prompt_builder.py`)

**统一提示词组装器**，所有 Agent 共用。

**固定顺序（保证跨 task 的 LLM 缓存命中率）**:
1. `skill/engineer/{type}.md` — Agent 专属技能
2. 工作区路径
3. **上游真理**（已生成模块的对外接口，LLM 提取的完整签名/字段，不可质疑）
4. `skill/code/quality.md` — 代码质量 + 三端运行时规范
5. `skill/code/readability.md` — 可读性
6. `skill/code/ui.md` — UI 设计（仅前端）
7. 额外指令（envConstraints 等）
8. 输出铁律（禁止总结、只能输出工具调用或完成消息）

**上游真理加载规则**（`_load_upstream_truths`）:
- 下层真理（`truth.type != agent_type`）→ 展示 `exposed_to_upper`
- 同层真理（`truth.type == agent_type`）→ 展示 `exposed_to_peers`
- 前端先生成（Layer 1），后端后生成（Layer 2）→ 后端可看到前端真理

**提示词模板**:
- `_USER_PROMPT_TEMPLATE` — 标准工程任务模板（含真理文件格式）
- `_INTEGRATION_USER_PROMPT_TEMPLATE` — 集成任务专用模板
- 每种 Agent 类型有专属的真理 JSON 模板（`_TRUTH_TEMPLATES`）

---

### 6.2 brainAgent/ — 编排调度器

#### 6.2.1 basic.py — 统一入口

**命令行**:
```bash
python brainAgent/basic.py "设计一个线上商城购物系统"          # 全流程
python brainAgent/basic.py -orchestrator "需求"               # 只跑需求分析
python brainAgent/basic.py -architect                         # 从架构开始
python brainAgent/basic.py -engineer                          # 从代码生成开始
python brainAgent/basic.py -test --fast                       # 从测试开始(快速模式)
```

**流程控制**: 通过 `-orchestrator`, `-architect`, `-engineer`, `-test` 标志控制起始阶段。所有标志之后的步骤都会执行。

**内置校验**:
- `_validate_code_generation()` — 对所有 JS 文件运行 `node --check`
- `_validate_env_consistency()` — 扫描代码中 `process.env.X` 引用，与 `.env` 对比，自动补全缺失变量

**测试多轮**: 测试阶段最多自动运行 10 轮，每轮调用 `run_scheduler()`。全部通过或停滞（通过数不再增长）时停止。

#### 6.2.2 orchestrator.py — 需求分析编排

- 管理 N 轮讨论（前 N-1 轮 discuss，最后一轮 final_output）
- 超时保护：discuss 600s，final_output 900s
- 降级 PRD 生成（LLM 失败时从 `full_summary.json` 自动生成）

#### 6.2.3 engineer.py — 工程调度器

- 契约关键字段校验
- 文件冲突检测（同一文件被多个任务声明）
- `build_layered()` 严格类型分层
- 逐层并发执行 + **依赖剪枝**（节点失败 → 递归剪枝全部后代）
- 集成任务独立执行
- `failed_tasks.json` 输出（含根因失败、剪枝任务、修复顺序）
- 执行报告生成

#### 6.2.4 scheduler.py — 测试调度器

详见 [第 10 节](#10-测试验证子系统abcd-循环)。

#### 6.2.5 knowledge_builder.py — 知识库构建器

详见 [第 9 节](#9-rag-知识库子系统)。

#### 6.2.6 retrieval_scheduler.py — 统一检索调度器

详见 [第 9 节](#9-rag-知识库子系统)。

---

### 6.3 localAgent/ — LLM 调用封装

| 文件 | 功能 | 调用的 LLM 任务 |
|------|------|----------------|
| `knowledge_builder.py` | 知识库构建 LLM 调用 | `refine`（经验净化）、`merge`（语义合并） |
| `retrieval_agent.py` | 检索 LLM 调用 | `angle_analysis`（查询分解）、`deliver`（结果格式化） |

---

### 6.4 utils/ — 共享工具

#### dependency_graph.py

**核心算法**: 严格类型分层拓扑排序。

1. 计算每个任务的拓扑深度（迭代至收敛，最大迭代次数防循环依赖）
2. 按 `(类型优先级, 拓扑深度)` 排序 — **类型优先于深度**
3. 同类型连续任务合并为一层 → LLM system prompt 缓存命中
4. 同类型内按深度拆分子层（有依赖关系的同类型任务分拆）

**类型优先级**（自底向上）:
```
repair(-1) < infra(0) < db(1) < frontend_static(1.5)
  < auth(2) < db_api(3) < peer_deps(3.5)
  < api(4) < backend_proc(4.5) < navigation(5)
  < logic(6) < scenario(7) < nfr(8)
```

**循环依赖检测**: 迭代超过 `len(tasks) * 10` 次未收敛 → 抛出 ValueError。

#### json_extractor.py

从 LLM 输出提取 JSON，多种策略按优先级尝试：
1. `<FILES_START>` 标签
2. `<MEMORY_START>` 标签
3. Markdown 代码块（`` ```json `` 或 `` ``` ``）
4. 原始 `{...}` 匹配（括号平衡）
5. `[...]` 匹配

#### logger.py

统一日志，双输出：
- stderr：WARNING 及以上
- 文件：DEBUG 及以上，按日轮转（`agent_YYYYMMDD.log`）

#### token.py

非侵入式 Token 追踪器，包装 Agent 事件流：
- 估算输入/输出 Token
- 计算成本（支持 DeepSeek 定价）
- 保存 JSON 报告到日志目录

---

### 6.5 Tools/ — 可复用工具

#### Tools/coding/ — 文件操作

| 工具 | 函数签名 | 说明 |
|------|----------|------|
| `create_file` | `(path, content, overwrite, workspace)` | 创建单个文件 |
| `create_files` | `(files[], overwrite, workspace, metadata)` | 批量创建，自动语法检查 |
| `delete_file` | `(path, workspace)` | 删除文件 |
| `edit_lines` | `(edits[], workspace)` | 按行号插入/替换/删除 |
| `modify_file` | `(path, content, workspace)` | 覆盖文件内容 |
| `read_file` | `(path, workspace)` | 读取文件 |
| `list_files` | `(directory, workspace)` | 列出目录（知识库构建用） |
| `get_functions_info` | `(path, workspace)` | 提取函数信息 |
| `syntax_check` | `(files[], workspace)` | `node --check` 语法检查 |

#### Tools/memory/ — 记忆管理

- **ban_memory.py**: 禁令记忆（fingerprint + prohibition instruction 对），支持去重存储、格式化注入、按 task_id + 类型隔离
- **load_memory.py**: 加载 JSON 记忆文件，支持默认值
- **save_memory.py**: 保存 JSON 记忆文件
- **merge_memory.py**: 合并讨论轮次摘要（模块级深度合并、实体去重、待决策问题去重）

#### Tools/contract/ — 契约处理

- **parser.py**: 解析 logic 契约 → 实现指令（事务边界、并发控制、补偿逻辑、错误映射）+ 测试场景生成

#### Tools/scoring/ — 代码评分

- **code_scorer.py**: 5 维度评分系统
  - 源码评分：测试通过率 30% + 任务完成度 25% + 测试覆盖率 20% + 代码质量 15% + 记忆修复率 10%
  - 测试代码评分：Mock 完整性 30% + 断言质量 25% + 场景覆盖 20% + 框架合规 15% + 语法 10%
  - 等级：S(≥95) / A(≥90) / B(≥80) / C(≥70) / D(<70)

#### Tools/rag/ — RAG 知识库

详见 [第 9 节](#9-rag-知识库子系统)。

#### Tools/testing/ — 测试执行

- **run_test.py**: 执行 Jest/Vitest 测试，解析 JSON 输出，提取失败信息（错误类型、期望值/实际值、堆栈）

#### Tools/skill/ — 技能加载

- **load_skill.py**: 从 `skill/` 目录加载 Markdown 文件作为 Agent 系统提示词的一部分

---

### 6.6 skill/ — Agent 技能文档 (~80+ 文件)

所有技能文档均为 Markdown 格式，在被加载时作为 Agent 的 system prompt 的一部分。

```
skill/
├── code/                         # 代码质量标准（所有 Agent 共用）
│   ├── quality.md                #   代码质量 + 三端运行时规范
│   ├── readability.md            #   可读性规范
│   └── ui.md                     #   前端 UI 设计（仅 frontend Agent）
├── design/                       # 产品经理角色卡片
│   ├── product_manager.md        #   PM 主技能（讨论和输出规范）
│   ├── customer.md               #   客户视角
│   ├── user.md                   #   用户视角
│   ├── manager.md                #   管理者视角
│   ├── innovator.md              #   创新者视角
│   ├── business_expert.md        #   业务专家视角
│   ├── qa.md                     #   质量视角
│   ├── data.md                   #   数据视角
│   ├── architect.md              #   架构视角
│   ├── security.md               #   安全视角
│   └── prd_template.md           #   PRD 输出模板
├── engineer/                     # 工程 Agent 角色定义
│   ├── architect.md              #   架构师
│   ├── backend.md                #   后端工程师
│   ├── frontend.md               #   前端工程师
│   ├── database.md               #   数据库设计师
│   ├── infrastructure.md         #   基础设施工程师
│   └── integrator.md             #   集成工程师
├── test/                         # 测试相关 (~50 文件)
│   ├── test_architect.md         #   测试架构设计规范
│   ├── a/                        #   A步: 测试编写诊断 (11 文件)
│   ├── b/                        #   B步: 测试运行诊断 (11 文件)
│   ├── c/                        #   C步: 源码修复 (11 文件)
│   ├── d/                        #   D步: 验证诊断 (11 文件)
│   ├── roles/                    #   各步骤角色定义
│   └── templates/                #   17 个测试模板
└── rag/                          # RAG Agent 指令
    ├── refine.md                 #   经验净化指令
    ├── merge.md                  #   语义合并指令
    ├── angle_analysis.md         #   查询分解指令
    ├── deliver.md                #   结果交付指令
    └── retrieval_skill.md        #   检索技能描述
```

---

### 6.7 config/ — 配置文件

| 文件 | 用途 |
|------|------|
| [config/env_defaults.json](config/env_defaults.json) | 14 个 Web 项目环境变量默认值（PORT, DB_HOST, JWT_SECRET 等），`infrastructure_designer.py` + `integrator.py` 使用 |
| [config/file_refs.json](config/file_refs.json) | 已知文件引用依赖映射（如 `middleware/auth.js` → `utils/response.js`），架构师自动注入跨任务依赖 |
| [config/infra_fixes.json](config/infra_fixes.json) | 基础设施自动修复模式（npm 包、babel 配置、Jest transform），integrator 使用 |
| [config/mock_factories.json](config/mock_factories.json) | 21 个 npm 包的 Jest Mock 工厂策略（express, mysql2, jsonwebtoken 等），test_writer 使用 |

---

## 7. 数据流

### 7.1 主流水线数据流

```
需求描述 (一句话)
  │
  ▼
[PM Agent] ──→ Memory/chat_sessions/{id}/full_memory.json   (完整讨论记录)
  │            Memory/chat_sessions/{id}/full_summary.json   (累计摘要)
  ▼
requirement_report_*.md  (PRD 报告)
  │
  ▼
[Architect Agent] ──→ work/project/task/task_*.json  (契约 + 任务)
  │
  ▼
[Engineer Scheduler]
  ├─── [Infra Agent]  ──→  Memory/truths/engineer/{infra_task}.json
  ├─── [DB Agent]     ──→  Memory/truths/engineer/{db_task}.json
  ├─── [Frontend Agent]──→ Memory/truths/engineer/{frontend_task}.json
  ├─── [Backend Agent] ──→ Memory/truths/engineer/{backend_task}.json
  └─── [Integrator]   ──→  .env 补全 + 最终校验
  │
  ▼
源代码 (work/project/)
  │
  ▼
[Test Scheduler] ──→ Memory/test_logs/{task_id}.json       (测试状态)
  │                  Memory/test_failure/{task_id}.json     (测试禁令)
  ▼                  Memory/source_failure/{task_id}.json   (源码禁令)
测试通过报告 + 评分
  │
  ▼
[Knowledge Builder] (可选) ──→ knowledge/  (LanceDB 经验库)
```

### 7.2 上游真理传递

```
工程师阶段:               测试阶段:
┌──────────────┐         ┌──────────────────────┐
│ Engineer Truths│───────→│ 注入到 Test Writer    │
│ (LLM 生成)     │         │ (作为 lower_truths)   │
│                │         │                      │
│ infra → db    │         │ 通过后提取 interface  │
│ db → frontend │         │ → Test Truths         │
│ frontend →    │         │ → 供下次 ABCD 循环     │
│   backend     │         └──────────────────────┘
└──────────────┘
```

- **Engineer Truth**: 代码生成阶段 LLM 主动声明接口（`exposed_to_upper` + `exposed_to_peers`）
- **Test Truth**: 测试通过后 LLM 精读源码提取，覆盖 Engineer Truth（更精确）
- 后一步任务通过 prompt_builder 的 `_load_upstream_truths()` 加载上游真理，约束输出

---

## 8. 依赖图与分层架构

### 8.1 分层执行原则

1. **同类型任务必须在连续层中执行** — 提高 LLM system prompt 缓存命中率
2. **不同类型任务不得在同一层并发** — 避免 prompt 前缀频繁切换
3. **类型优先于深度** — 确保所有 infra 在一起、所有 db 在一起
4. **同类型内部按拓扑深度拆分子层** — 有依赖关系的同类型任务拆分

### 8.2 执行顺序

```
Layer -1: repair        修复层（直接调 engineer，不走 ABCD）
Layer  0: infra         基础设施（middleware, utils, config, .env）
Layer  1: db            数据库（DDL, init-db.js）
Layer  1.5: frontend_static  前端（Vue 页面, Store, API, Router）
Layer  2: auth          Auth 层
Layer  3: db_api        数据库 API
Layer  3.5: peer_deps   同层依赖检查
Layer  4: api           API 层
Layer  4.5: backend_proc 后端业务处理
Layer  5: navigation    导航层
Layer  6: logic         业务逻辑层
Layer  7: scenario      场景层
Layer  8: nfr           非功能需求层
Layer 99: integration   集成层（单独执行）
```

### 8.3 依赖剪枝算法

```
节点 A 失败
  → 递归查找所有通过依赖链到达的节点 B, C, D...
  → 标记 B, C, D 为 "pruned"
  → 不执行被剪枝的任务
  → 输出 failed_tasks.json（区分 root_cause 和 pruned）
  → 修复顺序: 先修根因 → 根因修复后剪枝自动解除
```

---

## 9. RAG 知识库子系统

### 9.1 架构概览

```
Memory/test_failure, Memory/source_failure  (失败记忆)
  │
  ▼
[Knowledge Builder] — 6 步流水线
  │
  ├─ Step 0: 文件发现 — 扫描目录，分类 memory_files/task_files/source_files
  ├─ Step 1: 记忆过滤 — 清洗低价值记忆，保留 L3+
  ├─ Step 2: 锚点绑定 — 构建 测试任务 ↔ 架构任务 双任务映射链
  ├─ Step 3: LLM 净化 — run_knowledge_builder("refine") 深度经验提炼
  ├─ Step 4: 去重合并 — 指纹去重 + 语义相似度合并
  ├─ Step 5: 向量化存储 — SentenceTransformer 嵌入 → LanceDB
  └─ Step 6: 创建索引
  │
  ▼
knowledge/  (LanceDB 向量数据库)
  ├── knowledge_base 表    (经验 do/don't 模式)
  ├── code_base 表         (S/A 级源码)
  └── test_code_base 表    (S/A 级测试代码)
```

### 9.2 检索流程

```
Agent 调用 search_rag(query)
  │
  ▼
[Retrieval Scheduler] — 3 步流程
  │
  ├─ Step 1: angle_analysis — LLM 将查询分解为 3 个检索角度
  ├─ Step 2: 3×3 扩散搜索 — 每个角度 × 3 次搜索（不同过滤条件）
  │            └─ retrieve_single_angle() — LanceDB 向量搜索 + 锚点过滤
  ├─ Step 3: deliver — LLM 格式化结果（按 agent_type 定制格式）
  │
  ▼
Redis 缓存（24h TTL）→ 相同查询命中缓存
```

### 9.3 代码检索（双管道）

```
search_code(query)
  │
  ├─ Stage 1: BM25 + 向量混合检索 → 候选集
  └─ Stage 2: Reranker 重排序 → Top-K
  │
  ├── code_base 管道       (源码检索，agent_type ≠ test_*)
  └── test_code_base 管道  (测试代码检索，agent_type = test_*)
```

---

## 10. 测试验证子系统（ABCD 循环）

### 10.1 架构

```
[Test Scheduler] — 13 层 ABCD 循环
  │
  ├─ Layer -1 (repair):   直接调 engineer agent 重生成缺失文件
  ├─ Layer 0 (infra):     静态检查（middleware 导出、config 导出、env 一致性）
  ├─ Layer 1 (db):        静态对照（DDL vs Model 列名/类型一致性）
  ├─ Layer 1.5 (frontend_static): 静态检查（SFC 语法、import 路径、命名导出）
  ├─ Layer 2 (auth):     混合检查
  ├─ Layer 3 (db_api):    动态测试
  ├─ Layer 3.5 (peer_deps): 静态检查（同层依赖）
  ├─ Layer 4 (api):       动态测试
  ├─ Layer 4.5 (backend_proc): 动态测试
  ├─ Layer 5 (navigation): 动态测试
  ├─ Layer 6 (logic):     动态测试
  ├─ Layer 7 (scenario):  动态测试
  └─ Layer 8 (nfr):       动态测试
```

### 10.2 ABCD 循环逻辑

```
┌─────────────────────────────────────────────────────┐
│                   ABCD 单次循环                       │
│                                                       │
│  A: test_writer   → 生成测试文件                      │
│       │                                               │
│       ├─ 语法验证失败 → store_bans(test_failure) → 返回 │
│       │                                               │
│       ▼                                               │
│  B: test_runner   → 运行测试 + 诊断                   │
│       │                                               │
│       ├─ total=0 (测试框架问题) → store_bans → 返回    │
│       ├─ failed=0 + total>0 → ✅ 全部通过 → 返回       │
│       ├─ failed>0 + fix_target=test → store_bans → 返回│
│       └─ failed>0 + fix_target=source → 跳到 C        │
│                                                       │
│  C: source_fixer  → 修复源码                          │
│       │                                               │
│       ├─ 语法验证 → 失败则返回                          │
│       └─ 保存源码快照 (Redis/文件) → 跳到 D            │
│                                                       │
│  D: test_runner   → 验证修复                          │
│       │                                               │
│       ├─ total=0 / failed>0 → store_bans → 返回       │
│       └─ failed=0 → ✅ 全部通过 → 提取真理 → 评分入库  │
│                                                       │
│  每轮最多 3 次尝试 (max_attempts=3)                    │
│  尝试用尽且测试仍失败 → 删除测试文件 → 回滚到最佳版本   │
└─────────────────────────────────────────────────────┘
```

### 10.3 Redis 快照与回滚

- **快照**: 每次 Step C 执行前，保存当前源码的 MD5 哈希 → 文件/Redis
- **最佳版本**: 每次测试完全通过时，更新 best_score + best_hash
- **回滚**: 所有尝试用尽且仍失败时，恢复 best_hash 对应的源码快照
- **降级**: Redis 不可用时，降级为 `Memory/snapshots/` 文件快照

### 10.4 禁令系统（Ban System）

```
禁令指纹格式: {layer}|{source}|{category}|{type}
  e.g.: "infra|middleware|middleware/auth.js|MISSING"

禁令指令格式: "DON'T: {具体错误} | fix: {修复方向} | {test_subdir}"
  e.g.: "DON'T: 未导出 authenticate | fix: 添加 module.exports.authenticate | test/unit"

存储位置:
  Memory/test_failure/{task_id}.json    — 测试禁令
  Memory/source_failure/{task_id}.json  — 源码禁令

注入方式:
  - A 步: test_bans → 避免重复生成相同错误的测试
  - C 步: source_bans → 避免重复犯相同错误的源码
```

---

## 11. 运行时数据与存储

| 路径 | 内容 | 格式 |
|------|------|------|
| `knowledge/` | LanceDB 向量数据库（3 张表） | LanceDB |
| `Memory/chat_sessions/{id}/full_memory.json` | PM 完整讨论记录 | JSON |
| `Memory/chat_sessions/{id}/full_summary.json` | PM 累计摘要 | JSON |
| `Memory/test_failure/{task_id}.json` | 测试禁令 | JSON array |
| `Memory/source_failure/{task_id}.json` | 源码禁令 | JSON array |
| `Memory/test_logs/{task_id}.json` | 任务测试状态 | JSON |
| `Memory/truths/engineer/{task_id}.json` | Engineer 真理 | JSON |
| `Memory/truths/test/{task_id}.json` | Test 真理 | JSON |
| `Memory/agent_logs/engineer/{tid}/` | 工程师 Agent 日志 | .md + .json |
| `Memory/agent_logs/test/{tid}/attempt_{n}/` | 测试 Agent 日志 | .md + .json |
| `Memory/logs/agent_YYYYMMDD.log` | 系统日志 | 文本 |
| `Memory/snapshots/snap_{tid}_{hash}.json` | 源码快照 | JSON |
| `Memory/snapshots/best_{tid}.json` | 最佳版本元数据 | JSON |
| `work/project/` | 生成的项目代码 | 源码 |
| `work/project/task/task_*.json` | 架构计划 | JSON |
| `work/project/test/test_tasks_*.json` | 测试计划 | JSON |
| `work/project/doc/requirement_report_*.md` | PRD 报告 | Markdown |
| `work/project/report/execution_report_*.json` | 执行报告 | JSON |
| `work/project/.meta/` | 任务元数据 + failed_tasks.json | JSON |

---

## 12. 接口真理（Truth）系统

### 12.1 两层真理

| 类型 | 生成阶段 | 生成方式 | 存储位置 |
|------|----------|----------|----------|
| **Engineer Truth** | 代码生成 (Step 3) | LLM 主动声明（`_extract_exposed_interface`）+ 正则回退 | `Memory/truths/engineer/` |
| **Test Truth** | 测试验证 (Step 4) | 测试通过后 LLM 精读源码提取 + 正则回退 | `Memory/truths/test/` |

### 12.2 接口结构

每种 Agent 类型有专属的两层接口：

```json
{
  "exposed_to_upper": {
    // infra: middleware[], utils_exports[], config_exports[], env_vars_used[]
    // db: tables[] (含 fields/indexes/foreignKeys)
    // frontend: pages[], api_calls[], router{}
    // backend: routes[] (含 handlers/middleware/request/response)
  },
  "exposed_to_peers": {
    // infra: internal_exports[] (同层 import 依赖)
    // db: cross_table_refs[]
    // frontend: stores[] (含 state/actions/getters/imported_by)
    // backend: services[], cross_task_imports[]
  }
}
```

### 12.3 真理传递链

```
PrompBuilder._load_upstream_truths()
  │
  ├─ 从 Memory/truths/engineer/*.json 加载
  ├─ 按 agent_type 白名单过滤（如 backend 看 infra + db + frontend）
  ├─ 下层 → exposed_to_upper（上层需要知道的接口）
  ├─ 同层 → exposed_to_peers（同层 import 依赖）
  │
  ▼
编排到 system prompt 的 "上游真理" 部分
  → Agent 被告知: "以下接口已被测试验证为正确，不可质疑。"
```

### 12.4 真理一致性验证

`_validate_truth_consistency()`: LLM 声明的接口 vs 正则扫描实际文件的接口 → 交叉比对 → 不一致时输出 warning 日志（但不阻断执行，以 LLM 声明的为准）。

---

## 13. 评分系统

### 13.1 源码评分 (`score_code`)

| 维度 | 权重 | 说明 |
|------|------|------|
| 测试通过率 | 30% | `passed / total` |
| 任务完成度 | 25% | 目标文件是否全部存在且非空 |
| 测试覆盖率 | 20% | 测试文件覆盖的源码文件比例 |
| 代码质量 | 15% | 禁令数、文件大小合理性 |
| 记忆修复率 | 10% | 历史禁令在本轮是否已修复 |

### 13.2 测试代码评分 (`score_test_code`)

| 维度 | 权重 | 说明 |
|------|------|------|
| Mock 完整性 | 30% | 需 mock 的依赖是否全部覆盖 |
| 断言质量 | 25% | 断言数量、expect 覆盖率 |
| 场景覆盖 | 20% | 测试场景 vs 源码场景匹配度 |
| 框架合规 | 15% | Jest/Vitest 语法规范 |
| 语法 | 10% | 语法无误 |

### 13.3 自动入库

- 源码总分 ≥ 90 → 存入 `knowledge/code_base`
- 测试代码总分 ≥ 90 → 存入 `knowledge/test_code_base`
- 这是"左脑数据来源"——只有经过测试验证的高质量代码才进入知识库

---

## 14. 外部依赖

### 14.1 Python 包

| 包 | 用途 |
|------|------|
| `picoagents` | Agent 框架（Agent 创建、流处理、工具调度） |
| `openai` | OpenAI-compatible API 客户端（DeepSeek） |
| `python-dotenv` | .env 文件加载 |
| `redis` (redis.asyncio) | Redis 缓存（可选，降级为文件） |
| `lancedb` | 向量数据库 |
| `sentence-transformers` | 文本嵌入（Qwen3-Embedding-4B） |
| `FlagEmbedding` | 重排序模型（Qwen3-Reranker-4B） |

### 14.2 外部服务

| 服务 | 用途 | 地址 | 是否必需 |
|------|------|------|----------|
| DeepSeek API | LLM 推理 | `https://api.deepseek.com` | ✅ 必需 |
| Redis | 缓存 | `redis://localhost:6379/0` | ❌ 可选（文件降级） |
| MySQL | 项目数据库 | `localhost:3306` | ❌ 仅测试时 |
| llama-server | 本地 LLM | `http://localhost:3002` | ❌ 可选 |

### 14.3 目标项目依赖（自动安装）

- **后端**: express, mysql2, jsonwebtoken, bcryptjs, cors, dotenv, express-validator
- **前端**: vue 3, vite, pinia, axios, vue-router
- **测试**: jest, vitest, @vue/vue3-jest, jest-environment-jsdom

---

## 15. 关键设计模式

### 15.1 模板方法模式 (BaseDesigner)

`BaseDesigner` 定义主流程骨架，子类覆写钩子方法：
- `_has_json_retry()` — 是否 JSON 重试
- `_build_result()` — 构建返回值
- `_get_target_files()` — 获取目标文件

### 15.2 策略模式 (Prompt Builder)

`build_user_prompt()` 根据 `agent_type` 选择不同的契约过滤策略和真理模板。

### 15.3 分层并发 + 剪枝

同类型任务并发执行（缓存友好），上游失败递归剪枝下游（避免无效计算）。

### 15.4 禁令记忆 (Ban Memory)

失败经验以 `(fingerprint, prohibition)` 对存储，注入到后续 Agent 的 prompt 中，防止重复犯错。

### 15.5 LLM 主生成 + Python 正则回退

真理提取优先使用 LLM 精读源码（高质量但不保证输出），Python 正则扫描作为回退（100% 可靠但信息有限）。

### 15.6 Redis + 文件双写缓存

Redis 可用时使用 Redis（带 TTL），不可用时降级为 JSON 文件。写操作同时写两份。

### 15.7 降级策略

- PM Agent 未产出 PRD → 从 `full_summary.json` 自动生成
- Redis 不可用 → 文件快照（`Memory/snapshots/`）
- LLM 接口提取失败 → 正则扫描回退
- LLM 净化失败 → 使用原始数据
- 测试任务文件缺失 → 降级使用最新文件
- npm install 缺失包 → 自动安装

---

## 16. 错误处理与容错

### 16.1 各阶段的容错

| 阶段 | 错误处理 |
|------|----------|
| PM 讨论 | 单轮超时/异常 → 继续下一轮 |
| PM final_output | 超时/异常 → 降级 PRD |
| 架构设计 | 关键字段缺失 → 阻断执行（抛 ValueError） |
| 代码生成 | 单任务失败 → 剪枝下游 → 记录到 failed_tasks.json |
| JSON 解析错误 | 自动重试一次（带明确的修复方向） |
| Agent 流异常 | 捕获 ErrorEvent/FatalErrorEvent → 记录错误文本 |
| 测试执行 | 失败 ≤3 次重试 → 回滚到最佳版本 |
| npm install 失败 | 忽略，后续测试可能仍通过 |
| Redis 不可用 | 降级为文件快照 |
| 语法检查失败 | 不阻断，记录错误列表 |

### 16.2 循环依赖保护

`dependency_graph.py` 中拓扑排序有最大迭代次数保护（`len(tasks) * 10`），超过后抛出 `ValueError` 并列出可能的循环依赖节点。

### 16.3 Token 追踪

所有 Agent 流通过 `wrap_agent_stream()` 包装，实时估算 Token 消耗并保存报告，避免超出上下文窗口。

---

## 附录 A: 关键文件索引

| 文件 | 角色 | 行数 |
|------|------|------|
| [agent/base_designer.py](agent/base_designer.py) | 所有工程 Agent 基类 | ~450 |
| [agent/prompt_builder.py](agent/prompt_builder.py) | 统一提示词组装 | ~350 |
| [brainAgent/basic.py](brainAgent/basic.py) | 统一入口 | ~290 |
| [brainAgent/scheduler.py](brainAgent/scheduler.py) | 测试调度器（ABCD 循环） | ~1390 |
| [brainAgent/engineer.py](brainAgent/engineer.py) | 工程调度器（分层并发） | ~415 |
| [brainAgent/knowledge_builder.py](brainAgent/knowledge_builder.py) | 知识库构建（6 步） | ~360 |
| [brainAgent/orchestrator.py](brainAgent/orchestrator.py) | 需求分析编排 | ~130 |
| [utils/dependency_graph.py](utils/dependency_graph.py) | 依赖图分层 | ~176 |
| [agent/architect.py](agent/architect.py) | 架构师 Agent | ~400+ |
| [agent/product_manager.py](agent/product_manager.py) | PM Agent | ~300+ |
| [agent/test_writer.py](agent/test_writer.py) | 测试编写（Step A） | ~400+ |
| [agent/test_runner.py](agent/test_runner.py) | 测试诊断（Step B+D） | ~500+ |
| [agent/source_fixer.py](agent/source_fixer.py) | 源码修复（Step C） | ~300+ |
| [Tools/rag/build/tools.py](Tools/rag/build/tools.py) | RAG 构建工具 | ~400+ |
| [Tools/rag/code_retrieval/code_retrieval.py](Tools/rag/code_retrieval/code_retrieval.py) | 代码检索 | ~300+ |
| [Tools/scoring/code_scorer.py](Tools/scoring/code_scorer.py) | 代码评分 | ~200+ |

## 附录 B: CLI 用法

```bash
# 全流程（从需求到测试验证）
python brainAgent/basic.py "设计一个医院预约挂号系统"

# 只跑需求分析
python brainAgent/basic.py -orchestrator "设计一个在线教育平台"

# 从架构设计开始（跳过需求分析）
python brainAgent/basic.py -architect --requirement-report work/project/doc/requirement_report_xxx.md

# 从代码生成开始（跳过需求+架构）
python brainAgent/basic.py -engineer --task-file work/project/task/task_xxx.json

# 从测试开始（跳过需求+架构+代码）
python brainAgent/basic.py -test --fast

# 指定最大讨论轮数
python brainAgent/basic.py "需求" --max-rounds 5

# 知识库构建
python brainAgent/knowledge_builder.py
> build Memory/test_failure,Memory/source_failure,work/project/test,work/project/task

# 测试调度器独立运行
python brainAgent/scheduler.py ./work/project ./work/project/test/test_tasks_xxx.json
```

---

> **文档生成**: 基于 2026-06-29 完整代码扫描。  
> **维护**: 当系统架构变更时，请同步更新本文档。

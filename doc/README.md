# Agent 多智能体代码生成系统 — 系统文档

> **从一句话需求 → 完整 Web 应用（Node.js + Express + MySQL + Vue 3），全自动生成。**

---

## 一、系统概述

### 1.1 这是什么？

Agent 是一个**多智能体协作的代码生成系统**。用户只需输入一句话需求（如"设计一个电商平台"），系统自动完成需求分析、架构设计、代码生成、测试编写与修复的全流程，最终产出可直接运行的完整 Web 应用源码。

### 1.2 核心能力

| 阶段 | 功能 | 状态 |
|------|------|:---:|
| Step 1 需求分析 | PM Agent + 10 角色子Agent 多轮讨论 → PRD 报告 | ✅ |
| Step 2 架构设计 | Architect Agent 流水线 → 7 类契约 + 5 类工程任务 | ✅ |
| Step 3 代码生成 | 5 类工程师分层并发 + 集成 → 完整源码 | ✅ |
| Step 4a 测试架构 | TestArchitect Agent → 分层测试任务清单 | ✅ |
| Step 4b ABCD 循环 | A 写测试 → B 诊断 → C 修复源码 → D 验证，多轮收敛 | 🚧 |

### 1.3 生成物示例

一次典型运行（电商平台）可产出：

| 类型 | 数量 | 说明 |
|------|------|------|
| 后端路由 | 12+ | Express 路由 + 中间件 + 数据库连接 |
| 前端页面 | 40+ | Vue 3 页面（用户端 + 商家端 + 管理后台） |
| SQL 表 | 12+ | 用户/商品/订单/优惠券/退款等完整 DDL |
| 测试计划 | 1 | 分层测试任务清单（含 checkPoints） |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     brainAgent/basic.py                      │
│                     (统一入口 & 5 阶段编排)                    │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  orchestrator   │  │   architect     │  │   engineer      │
│  需求分析编排    │  │  架构设计流水线  │  │  代码生成调度    │
│  (PM + 10角色)  │  │  (7类契约+任务)  │  │  (5类工程师)    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ test_architect  │  │   scheduler     │  │  source_fixer   │
│ 测试任务生成     │  │  ABCD 循环调度  │  │  源码修复       │
│ (分层流水线)     │  │  (A→B→C→D)     │  │  (静态+动态)    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 2.2 目录结构

```
Agent/
├── agent/                  # 核心 Agent 实现 (9 文件)
│   ├── product_manager.py   # PM Agent + 10 角色子Agent
│   ├── architect.py         # 架构师 — 5 步契约生成流水线
│   ├── base_designer.py     # 工程师基类 (infra/db/backend/frontend)
│   ├── integrator.py        # 集成工程师 — 全链路集成
│   ├── prompt_builder.py    # 统一提示词组装器
│   ├── test_architect.py    # 测试架构师 — 分层测试任务生成
│   ├── test_writer.py       # 测试编写 Agent (A 步骤)
│   ├── test_runner.py       # 测试诊断/验证 Agent (B/D 步骤)
│   └── source_fixer.py      # 源码修复 Agent (C 步骤)
│
├── brainAgent/              # 编排调度层 (6 文件)
│   ├── basic.py             # 统一入口 — 5 阶段全流程
│   ├── orchestrator.py      # 需求分析编排器 (PM + 角色调度)
│   ├── engineer.py          # 代码生成调度器 (DAG 分层并发)
│   ├── scheduler.py         # 测试调度器 (ABCD 循环 + 静态检查)
│   ├── knowledge_builder.py # 知识库构建
│   └── retrieval_scheduler.py # 检索调度
│
├── skill/                   # Agent 技能文档 (121 文件)
│   ├── design/              # 需求分析角色技能 (11 文件)
│   │   ├── product_manager.md  # PM 任务规划师技能
│   │   ├── customer.md / user.md / manager.md / ...
│   │   └── prd_template.md     # PRD 输出模板
│   ├── engineer/            # 工程技能 (7 文件)
│   │   ├── architect/       # 架构师技能 (5 文件)
│   │   │   ├── scene_tree.md   # 场景树规划
│   │   │   ├── data.md         # 数据层契约
│   │   │   ├── interfaces.md   # 接口层契约
│   │   │   ├── business.md     # 业务层契约
│   │   │   └── tasks.md        # 任务分配
│   │   └── code_generation/ # 代码生成技能 (5 文件)
│   │       ├── infrastructure.md / database.md / backend.md
│   │       ├── frontend.md / integrator.md
│   ├── test/                # 测试技能 (100+ 文件)
│   │   ├── architect/       # 测试架构师技能
│   │   ├── roles/a/         # A 步骤角色 (测试编写)
│   │   ├── diagnosis/b/     # B 步骤角色 (测试诊断)
│   │   ├── roles/c/         # C 步骤角色 (源码修复)
│   │   ├── diagnosis/d/     # D 步骤角色 (修复验证)
│   │   ├── repair/          # 修复策略
│   │   ├── templates/       # 测试模板
│   │   └── truths/          # 真理格式定义
│   ├── code/                # 代码规范 (3 文件)
│   │   ├── quality.md       # 通用代码质量规范
│   │   ├── readability.md   # 代码可读性规范
│   │   └── workflow.md      # 工具调用与执行流程
│   └── rag/                 # RAG 检索技能
│
├── Tools/                   # 可复用工具 (30 文件)
│   ├── coding/              # 代码操作工具
│   │   ├── create_file(s).py  # 文件创建
│   │   ├── read_file.py       # 文件读取
│   │   ├── modify_file(s).py  # 文件修改
│   │   ├── edit_lines.py      # 行级编辑
│   │   ├── list_files.py      # 文件列表
│   │   ├── syntax_check.py    # 语法检查
│   │   ├── quick_check.py     # 快速检查
│   │   ├── delete_file.py     # 文件删除
│   │   └── get_functions_info.py # 函数信息提取
│   ├── testing/             # 测试工具
│   │   ├── run_test.py        # 测试运行
│   │   └── npm_install.py     # npm 安装
│   ├── memory/              # 记忆工具
│   │   ├── save_memory.py     # 保存记忆
│   │   ├── load_memory.py     # 加载记忆
│   │   ├── ban_memory.py      # Ban 记忆管理
│   │   └── merge_memory.py    # 记忆合并
│   ├── rag/                 # RAG 检索工具
│   │   ├── search_rag.py      # RAG 搜索
│   │   ├── search_code.py     # 代码搜索
│   │   ├── retrieval/tools.py # 检索工具集
│   │   ├── build/tools.py     # 知识库构建
│   │   └── code_retrieval/    # 代码检索
│   ├── contract/            # 契约工具
│   │   └── parser.py          # 契约解析
│   ├── scoring/             # 评分工具
│   │   └── code_scorer.py     # 代码评分
│   └── skill/               # 技能加载
│       └── load_skill.py      # 技能加载器
│
├── utils/                   # 共享工具 (9 文件)
│   ├── model_client.py       # LLM 客户端单例
│   ├── token_tracker.py      # Token 消耗追踪
│   ├── token.py              # Token 流处理
│   ├── dependency_graph.py   # 依赖图构建 (DAG 分层)
│   ├── logger.py             # 日志工具
│   ├── json_extractor.py     # JSON 提取器
│   ├── file_scanner.py       # 文件扫描
│   ├── placeholder_files.py  # 占位文件生成
│   └── _gen_db_scripts.py    # 数据库脚本生成
│
├── localAgent/              # 本地 LLM Agent 调用器 (2 文件)
│   ├── knowledge_builder.py  # RAG 知识构建 (refine 经验净化 + merge 语义合并)
│   └── retrieval_agent.py    # RAG 检索 Agent (angle_analysis 角度分析 + deliver 结果交付)
│
├── Memory/                  # 运行时记忆存储
│   ├── agent_logs/          # Agent 对话日志
│   ├── truths/               # Agent 产出的真理文件
│   ├── chat_sessions/       # 需求分析会话
│   ├── architect/           # 架构师中间产物
│   ├── test_architect/      # 测试架构师中间产物
│   ├── test_logs/           # 测试状态记录
│   ├── test_failure/        # 测试失败 ban 记录
│   ├── source_failure/      # 源码失败 ban 记录
│   ├── token/               # Token 消耗快照
│   └── ui_styles/           # UI 风格文档 (PM+Designer 产出)
│
├── work/project/            # 生成产物（运行输出）
│   ├── routes/              # 后端 API 路由
│   ├── controllers/         # 控制器
│   ├── services/            # 业务逻辑层
│   ├── middleware/          # 认证/权限/错误处理
│   ├── config/              # 数据库/日志配置
│   ├── database/            # DDL 脚本 + 种子数据
│   ├── src/                 # Vue 3 前端
│   │   ├── pages/           # 页面组件
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── router/          # 前端路由
│   │   ├── api/             # API 调用模块
│   │   └── components/      # 公共组件
│   ├── test/                # 测试文件
│   └── task/                # 任务文件 + 场景树
│
├── config/                  # 配置文件
├── doc/                     # 文档
├── .env.example             # 环境变量模板
├── requirements.txt         # Python 依赖
└── setup.bat                # Windows 一键安装脚本
```

---

## 三、五阶段流水线详解

### 3.1 阶段 1：需求分析（Orchestrator）

**入口**：[brainAgent/orchestrator.py](../brainAgent/orchestrator.py)
**核心 Agent**：[agent/product_manager.py](../agent/product_manager.py)

**流程**：
1. PM Planner 读取当前摘要 → 输出本轮 plan JSON（分配角色 + focus）
2. Python 调度器按 Wave 并发执行角色子Agent
   - **Wave 1**：customer、user、innovator（无依赖）
   - **Wave 2**：manager、business、security、data、architect、qa、designer
3. 合并各角色 summary JSON → 更新 full_summary.json
4. 多轮迭代（默认 5 轮，含 final_output）
5. PM 读取完整记忆 + PRD 模板 → 输出最终 PRD markdown

**10 个角色子Agent**：

| 角色 | 职责 | 归属字段 |
|------|------|---------|
| customer | 商业价值、ROI、分期优先级 | `p` |
| user | 终端用户体验、前台功能 | `f` |
| manager | 运营效率、后台管理 | `b` |
| innovator | 竞品差异化、创新 | `i` |
| business | 行业标准功能模板 | — |
| qa | 边界场景、验收标准 | `t` |
| data | 实体关系、字段约束 | `d` |
| architect | 技术可行性、成本估算 | `c` |
| security | 安全基线、合规 | — |
| designer | 全局视觉风格、组件设计 | `ui` |

**产物**：`work/project/doc/requirement_report_*.md`（PRD 报告）

---

### 3.2 阶段 2：架构设计（Architect）

**入口**：[agent/architect.py](../agent/architect.py)

**5 步流水线**（plan_tree → data → interfaces → business → tasks）：

```
Step 0: plan_tree    — 自上而下全局规划，含 §7 覆盖计数表
Step 1: data         — 自下而上第1层：model + auth 契约（无依赖）
Step 2: interfaces   — 自下而上第2层：api + db-api + navigation（并发）
Step 3: business     — 自下而上第3层：scenario + logic
Step 4: tasks        — 自下而上第4层：5 类任务分配 + 显式依赖链
Step 5: Merge        — 合并验证 → 输出 task_<ts>.json
```

**7 类契约**：

| 契约类型 | 说明 | 生成层 |
|---------|------|--------|
| model | 数据表结构（字段/类型/约束/索引/FK） | data |
| auth | 认证配置（JWT 策略/登录/注册/刷新） | data |
| api | HTTP 接口（method/path/request/response） | interfaces |
| db-api | 数据库操作 CRUD | interfaces |
| navigation | 页面跳转关系 | interfaces |
| scenario | 业务流程编排 | business |
| logic | 业务逻辑（输入/输出/事务边界） | business |

**5 类工程任务**：

| 类型 | 说明 | 优先级 |
|------|------|:---:|
| infra | 基础设施（package.json/env/中间件/工具函数） | 1 |
| db | 数据库（DDL/种子数据） | 2 |
| frontend | 前端（Vue 3 页面/路由/状态管理/API 模块） | 3 |
| backend | 后端（Express 路由/控制器/服务层） | 3 |
| integration | 集成（路由注册/env 配置/Vite 构建/DB 初始化） | 4 |

**核心机制**：
- §7 计数校验：每层生成前强制计数，不足则补全
- 参数提取表：写 JSON 前先枚举全部应生成项
- "从 plan_tree 原文复制"铁律：禁止重新表述
- max_iter=3~4：给模型自我纠错空间

**产物**：`work/project/task/task_*.json`（契约 + 任务清单）

---

### 3.3 阶段 3：代码生成（Engineer）

**入口**：[brainAgent/engineer.py](../brainAgent/engineer.py)

**执行模型**：
1. 加载 task JSON → 提取 tasks + contracts
2. DAG 拓扑排序 → 按类型分层
3. 逐层并发执行（同层任务共享 system prompt，最大化缓存命中）
4. 集成任务最后执行

**分层执行顺序**：infra → db → frontend → backend → integration

**每层内部**：同类型任务并发执行（通过 [utils/dependency_graph.py](../utils/dependency_graph.py) 保证拓扑正确）

**工程师 Agent 执行流程**（4 步）：

```
Step 1 — 搜集（可选）: search_rag + search_code 并行
Step 2 — 创建（必须）: create_files 一次性创建全部 outputFiles
Step 3 — 修复（按需）: edit_files 或 create_files，最多 2 次
Step 4 — 真理（必须）: 输出真理 JSON（接口签名/导出清单）
```

**真理传递机制**：
- 每个工程师 Agent 完成任务后输出"真理 JSON"（`exposed_to_upper` + `exposed_to_peers`）
- 下游 Agent 通过 [agent/prompt_builder.py](../agent/prompt_builder.py) 的 `_load_upstream_truths()` 加载直接依赖的真理
- 真理中的字段名/函数签名/表结构被视为绝对正确，不可质疑

**集成 Agent**（[agent/integrator.py](../agent/integrator.py)）额外执行：
- 预扫描：require/import 路径断裂检测
- 自动注入缺失路由
- 多路由导出展开
- 死路由清理
- env 变量补全
- Vite 构建验证
- 全链加载测试

**产物**：`work/project/` 下的完整项目源码

---

### 3.4 阶段 4：测试架构生成（Test Architect）

**入口**：[agent/test_architect.py](../agent/test_architect.py)

**流程**（与架构师相同的流水线模式）：

```
Step 0: 测试场景树   — 从上往下全量规划
Step 1: 静态层       — infra/db/frontend/peer_deps/integ
Step 2: 接口层       — auth/db_api/api/navigation（分 4 子步）
Step 3: 逻辑层       — backend_proc/logic/scenario
Step 4: 质量层       — nfr（性能/安全/并发）
Step 5: 合并         — 去重 + 插入 repair 占位任务
```

**测试任务结构**：
```json
{
  "id": "t_auth_001",
  "layer": "auth",
  "testType": "interface",
  "sourceTask": "t_backend_auth_01",
  "targetFiles": ["middleware/auth.js"],
  "dependencies": ["t_infra_001"],
  "testFramework": "jest",
  "checkPoints": ["导出 authenticate", "导出 optionalAuth"],
  "testScenarios": [
    {"category": "correct", "scenario": "有效 token → 200"},
    {"category": "error", "scenario": "过期 token → 401"}
  ]
}
```

**产物**：`work/project/test/test_tasks_*.json`

---

### 3.5 阶段 5：测试与修复执行（ABCD 循环）

**入口**：[brainAgent/scheduler.py](../brainAgent/scheduler.py)

**ABCD 循环**（4 步迭代，多轮收敛）：

```
A (test_writer)  → 基于模板 + 场景 + 真理生成测试代码
B (test_runner)  → 跑测试 → 诊断失败 → 输出 ban (f=指纹|b=修复指令)
C (source_fixer) → 接收 ban → 读取源码 → 定点修复
D (test_runner)  → 重新跑测试 → 验证修复 → 输出真理 或 新 ban
```

**Ban 记忆系统**（[Tools/memory/ban_memory.py](../Tools/memory/ban_memory.py)）：
- 测试失败 → 写入 `Memory/test_failure/{task_id}.json`
- 源码问题 → 写入 `Memory/source_failure/{task_id}.json`
- 跨 attempt 持久化，积累有效经验
- 每轮末清理已通过任务的无效 ban

**4 大测试类型**（按依赖顺序执行）：

| 类型 | 子层 | 执行模式 |
|------|------|---------|
| static | infra / db / frontend / peer_deps / integ | 直通（Python 静态检查 → Agent 修复 → 真理验证） |
| interface | auth / db_api / api / navigation | ABCD 循环 |
| logic | backend_proc / logic / scenario | ABCD 循环 |
| quality | nfr（k6 性能测试） | ABCD 循环 |

**双层屏障机制**：
- 屏障 1（C→D 解锁）：B/C/smoke 全部完成
- 屏障 2（D→下轮解锁）：D 全部完成
- 保证并发安全：同层并行，跨层串行

---

## 四、关键技术设计

### 4.1 多智能体协作模式

系统采用**分层角色模型**：

1. **PM + 角色讨论模式**（需求分析阶段）
   - PM 负责规划，10 个角色负责领域深度
   - 多轮收敛：R1 主干 → R2-R4 枝干 → R5 最终输出
   - 角色间互不知晓对方输出（由 PM 汇总裁决）

2. **流水线模式**（架构设计阶段）
   - 每层读取前序全部产出
   - 从上往下规划（plan_tree）+ 从下往上生成（data→interfaces→business→tasks）
   - 计数校验保证覆盖率

3. **分层并发模式**（代码生成阶段）
   - DAG 拓扑排序 → 同类型分层
   - 层间串行（保证依赖），层内并行（最大化效率）
   - 真理传递保证接口一致性

4. **ABCD 循环模式**（测试阶段）
   - 4 个 Agent 接力：写测试 → 诊断 → 修复 → 验证
   - Ban 记忆跨轮次传递，逐步收敛

### 4.2 契约驱动开发

所有下游工作基于**结构化契约**而非自然语言：

- 架构师生成 7 类契约（model/auth/api/db-api/navigation/scenario/logic）
- 工程师严格按契约生成代码（字段名/路径/签名不可偏离）
- 测试架构师基于契约生成测试场景
- 真理文件在 Agent 间传递接口信息

### 4.3 技能系统（Skill）

121 个 Markdown 技能文件构成**分层知识体系**：

- **设计层**（`skill/design/`）：各角色的领域知识、PRD 模板
- **工程层**（`skill/engineer/`）：架构规范、代码生成指南
- **测试层**（`skill/test/`）：测试架构、诊断策略、修复策略、模板、真理格式
- **规范层**（`skill/code/`）：代码质量、可读性、工作流

技能加载策略：
- 共享技能（如 workflow.md）注入所有 Agent
- 类型专属技能按 Agent 类型注入
- 测试技能按 layer + testType 动态组合加载

### 4.4 真理与 Ban 记忆系统

**真理（Truth）**：
- 工程师 Agent 完成任务后输出结构化真理 JSON
- 包含 `exposed_to_upper`（给下游）和 `exposed_to_peers`（给同层）
- 下游 Agent 通过 `_load_upstream_truths()` 加载直接依赖的真理
- 真理中的接口签名被视为绝对正确

**Ban（禁令）**：
- 格式：`f=layer|source/test|file:line|TYPE` + `b=DON'T: ... | fix: ...`
- 测试失败 → B 步骤输出 ban → C 步骤按 ban 修复
- 持久化到 Memory，跨 attempt 累积
- 每轮末自动清理已通过任务的无效 ban

### 4.5 Prompt 缓存优化

[agent/prompt_builder.py](../agent/prompt_builder.py) 采用固定顺序组装提示词：

1. 通用代码质量规范（所有 Agent 共享 → 缓存命中）
2. 代码可读性规范（所有 Agent 共享 → 缓存命中）
3. 工具调用与执行流程（所有 Agent 共享 → 缓存命中）
4. 场景树（业务上下文）
5. UI 风格文档（仅前端）
6. Agent 专属 skill
7. 上游真理（优先级最低）

这种分层设计最大化跨 task 的 prompt 缓存命中率。

### 4.6 Token 消耗追踪

[utils/token_tracker.py](../utils/token_tracker.py) 在每个阶段开始/结束时：
- 查询 DeepSeek API 余额
- 记录阶段消耗
- 持久化到 `Memory/token/{阶段名}.json`
- 支持历史趋势分析

---

## 五、快速开始

### 5.1 环境要求

- **Python** 3.11+
- **Node.js**（生成的产物需要，框架本身不需要）
- **MySQL**（生成的产物需要，测试阶段需要）
- **Redis**（可选，用于缓存）

### 5.2 安装

```bash
# Windows 一键安装
setup.bat

# 或手动安装
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY（DeepSeek API Key）
```

### 5.3 运行

```bash
# 全流程（从需求到测试）
python brainAgent/basic.py "设计一个电商平台"

# 分阶段运行
python brainAgent/basic.py -orchestrator "需求"    # 只做需求分析
python brainAgent/basic.py -architect              # 从架构设计开始
python brainAgent/basic.py -engineer               # 从代码生成开始
python brainAgent/basic.py -engineer --resume      # 恢复模式（跳过已完成任务）
python brainAgent/basic.py -test                   # 只跑测试执行
python brainAgent/basic.py -test --fast            # 快速测试模式

# 高级参数
python brainAgent/basic.py "需求" \
  --session-id my_project \
  --max-rounds 5 \
  --requirement-report path/to/report.md \
  --task-file path/to/task.json
```

### 5.4 配置说明

主要环境变量（[.env.example](../.env.example)）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | DeepSeek API Key | — |
| `OPENAI_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `OPENAI_MODEL` | 模型名称 | `deepseek-v4-pro` |
| `LOCAL_OPENAI_BASE_URL` | 本地 llama-server 地址 | `http://localhost:3002/completion` |
| `DB_HOST/PORT/USER/PASSWORD/NAME` | 数据库配置 | localhost:3306 |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` |
| `RAG_EMBEDDING_MODEL` | 向量嵌入模型 | `Qwen/Qwen3-Embedding-4B` |

---

## 六、核心依赖

| 包 | 用途 |
|------|------|
| [picoagents](https://pypi.org/project/picoagents/) | Agent 框架（含 LLM 客户端） |
| python-dotenv | 环境变量管理 |
| lancedb | 向量数据库（RAG 知识库） |
| sentence-transformers | Embedding 模型 |
| redis | 缓存（可选，不可用时降级为文件存储） |
| numpy / pyarrow | 数据处理 |

---

## 七、技术栈（生成产物）

系统生成的 Web 应用使用以下技术栈：

| 层 | 技术 |
|------|------|
| 后端运行时 | Node.js + Express |
| 数据库 | MySQL + mysql2 |
| 认证 | JWT (jsonwebtoken + bcrypt) |
| 前端框架 | Vue 3 (Composition API) |
| 构建工具 | Vite |
| 状态管理 | Pinia |
| UI 框架 | Element Plus |
| HTTP 客户端 | Axios |
| 测试框架 | Jest + supertest |
| 性能测试 | k6 |

---

## 八、路线图

```
✅ Step 1  需求分析      PM Agent 多角色讨论 → PRD 报告
✅ Step 2  架构设计      Architect Agent → 7 类契约 + 5 类任务
✅ Step 3  代码生成      5 类工程师分层并发 + 集成 → 完整源码
✅ Step 4a 测试架构      TestArchitect Agent → 测试任务清单
🚧 Step 4b ABCD 循环    测试运行 + 自动修复（加强中）
📋 Step 5  自动部署      Docker 容器化 + 一键部署
📋 Step 6  增量迭代      需求变更 → 增量更新（非全量重建）
```

---

## 九、License

MIT

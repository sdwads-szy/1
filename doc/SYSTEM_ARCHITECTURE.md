# Agent 多智能体代码生成系统 — 系统架构设计

---

## 第一章：系统总览

### 1.1 系统定位

Agent 是一个**多智能体协作的全自动代码生成系统**。它接收一句话自然语言需求作为输入，通过五个阶段的智能体协作流水线，产出可运行的完整 Web 应用（Node.js + Express + MySQL + Vue 3），包括需求文档、架构契约、前后端源码、数据库 DDL、测试代码。

### 1.2 核心设计理念

| 原则 | 说明 | 实现方式 |
|------|------|---------|
| **契约驱动** | 所有下游工作基于结构化数据，而非自然语言 | 7 类 JSON 契约贯穿全流程 |
| **分层解耦** | 每个阶段有明确的输入/输出边界 | 5 阶段流水线 + 文件落盘 |
| **真理传递** | Agent 间通过"真理文件"共享已验证的接口信息 | `exposed_to_upper` / `exposed_to_peers` |
| **Ban 经验积累** | 失败经验跨 attempt 持久化，避免重复犯错 | Memory 目录持久化 |
| **缓存优先** | System prompt 固定排序，最大化 LLM 缓存命中 | prompt_builder 5 层固定顺序 |
| **并发执行** | 无依赖任务并行，有依赖任务串行 | DAG 拓扑排序 + asyncio.gather |
| **可恢复** | 任何阶段失败后可从中断点继续 | `--resume` 模式 + 状态持久化 |

### 1.3 技术栈

| 层次 | 框架自身 | 生成产物 |
|------|---------|---------|
| 语言 | Python 3.11+ | JavaScript (Node.js) |
| Agent 框架 | picoagents | — |
| LLM | DeepSeek (OpenAI 兼容 API) | — |
| 后端运行时 | — | Node.js + Express |
| 数据库 | LanceDB (向量) + MySQL (产物) | MySQL + mysql2 |
| 前端 | — | Vue 3 + Vite + Pinia + Element Plus |
| 缓存 | Redis (可选) | — |
| 向量模型 | sentence-transformers | — |
| 测试 | — | Jest + supertest + k6 |

---

## 第二章：整体架构

### 2.1 分层架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        用户界面层                                  │
│                 brainAgent/basic.py (CLI 入口)                     │
│                   python brainAgent/basic.py "需求"                │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                       编排调度层 (brainAgent/)                      │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ orchestrator │  │  engineer    │  │     scheduler         │   │
│  │ 需求分析编排  │  │ 代码生成调度  │  │  ABCD 测试调度        │   │
│  │ PM+10角色     │  │ DAG分层+并发 │  │  双层屏障+静态检查     │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────────────────────────────┐     │
│  │ knowledge_   │  │        retrieval_scheduler            │     │
│  │ builder      │  │        检索调度 (RAG 查询路由)         │     │
│  └──────────────┘  └──────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                      核心 Agent 层 (agent/)                        │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ product_   │  │ architect  │  │ base_      │  │ integrator│ │
│  │ manager    │  │ 架构师      │  │ designer   │  │ 集成工程师 │ │
│  │ PM+10角色   │  │ 5步流水线   │  │ 4类工程师基类│  │ 全链路集成 │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ prompt_    │  │ test_      │  │ test_       │  │ test_     │ │
│  │ builder    │  │ architect  │  │ writer      │  │ runner    │ │
│  │ 提示词组装  │  │ 测试架构师  │  │ A步:测试编写 │  │ B/D步     │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
│                                                                  │
│  ┌────────────┐                                                  │
│  │ source_    │  C步: 源码修复                                    │
│  │ fixer      │                                                  │
│  └────────────┘                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                      技能系统层 (skill/)                           │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ design/    │  │ engineer/  │  │ test/       │  │ code/     │ │
│  │ 11 文件    │  │ 12 文件    │  │ 100+ 文件   │  │ 3 文件    │ │
│  │ 需求角色    │  │ 架构+代码   │  │ 测试全线     │  │ 质量规范   │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                      工具系统层 (Tools/)                           │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ coding/    │  │ testing/   │  │ memory/    │  │ rag/      │ │
│  │ CRUD+语法  │  │ Jest+k6+npm│  │ 记忆+Ban   │  │ 检索+构建  │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                      基础设施层 (utils/ + localAgent/)              │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ model_     │  │ token_     │  │ dependency_│  │ local     │ │
│  │ client     │  │ tracker    │  │ graph      │  │ Agent     │ │
│  │ LLM 客户端  │  │ Token 追踪  │  │ DAG 分层    │  │ 本地模型   │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              localAgent 子系统                              │ │
│  │  ┌─────────────────────┐  ┌─────────────────────────────┐  │ │
│  │  │ knowledge_builder   │  │ retrieval_agent             │  │ │
│  │  │ RAG 知识构建 Agent   │  │ RAG 检索 Agent              │  │ │
│  │  │ refine + merge      │  │ angle_analysis + deliver    │  │ │
│  │  └─────────────────────┘  └─────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流全景

```
一句话需求
    │
    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 1: 需求分析                                                │
│  需求 → PM planner → 10角色讨论(N轮) → PRD                        │
│  产物: work/project/doc/requirement_report_*.md                   │
│  中间: Memory/chat_sessions/{id}/full_memory.json + full_summary  │
│        Memory/ui_styles/*.md (Designer 产出的 UI 风格文档)         │
└──────────────────────────────────────────────────────────────────┘
    │ PRD (markdown)
    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 2: 架构设计                                                │
│  PRD → plan_tree → data契约 → interfaces契约 → business契约 → tasks │
│  产物: work/project/task/task_*.json (契约 + 任务)                 │
│  中间: work/project/task/_scene_tree.md                           │
│        Memory/architect/_contracts_*.json (中间契约)               │
│        Memory/architect/_tasks.json                               │
└──────────────────────────────────────────────────────────────────┘
    │ task.json (contracts + tasks)
    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 3: 代码生成                                                │
│  tasks → DAG分层 → [infra→db→frontend→backend→integration]        │
│  每层: 并发执行同类型任务 → 输出真理 JSON                            │
│  产物: work/project/ 完整项目源码                                   │
│  真理: Memory/truths/engineer/{taskId}.json                        │
└──────────────────────────────────────────────────────────────────┘
    │ 项目源码 + 真理
    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 4: 测试架构                                                │
│  源码+task+PRD → test_plan_tree → static→interface→logic→quality   │
│  产物: work/project/test/test_tasks_*.json                         │
│  中间: Memory/test_architect/_test_*.json                          │
└──────────────────────────────────────────────────────────────────┘
    │ test_tasks.json
    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 5: ABCD 测试循环                                           │
│  For each layer:                                                  │
│    A(test_writer) → B(test_runner) → C(source_fixer) → D(verify)  │
│  产物: test/*.test.js + Memory/test_logs/*.json                    │
│  Ban: Memory/test_failure/*.json + Memory/source_failure/*.json   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 第三章：核心子系统设计

### 3.1 需求分析子系统

#### 3.1.1 架构概览

```
                    ┌──────────────────┐
                    │   PM Planner     │
                    │  (product_manager│
                    │   .md skill)     │
                    └────────┬─────────┘
                             │ plan JSON
                             ▼
              ┌──────────────────────────────┐
              │     orchestrator.py          │
              │  Wave 1: customer/user/      │
              │          innovator           │
              │  Wave 2: manager/business/   │
              │   security/data/architect/   │
              │   qa/designer                │
              └──────────────┬───────────────┘
                             │ 并发调用
              ┌──────────────┼──────────────┐
         ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
         │RoleSub   │   │RoleSub   │   │RoleSub   │
         │Agent     │   │Agent     │   │Agent     │
         │(customer)│   │(user)    │   │(...)     │
         └────┬─────┘   └────┬─────┘   └────┬─────┘
              │ summary_json  │              │
              └──────────────┼──────────────┘
                             ▼
              ┌──────────────────────────────┐
              │   merge_role_summaries()     │
              │   合并 modules + entities    │
              │   + pending                  │
              └──────────────────────────────┘
```

#### 3.1.2 RoleSubAgent 设计

```python
# agent/product_manager.py — 核心类
class RoleSubAgent:
    def __init__(self, role_name: str, model_client):
        # 加载角色专用 skill (skill/design/{role}.md)
        self.skill_content = skill_file.read_text("utf-8")

    async def speak(self, context: dict, save_dir: str) -> dict:
        # 1. 构建 instructions (角色 skill + 上下文)
        # 2. 构建 user_prompt (本轮 focus + 模块树)
        # 3. 创建 Agent (max_iterations=1 纯推理, =3 designer 有写文件工具)
        # 4. 流式执行 + 提取 summary JSON
        # 5. 自存完整回答到 Memory/agent_logs/pm/
        return {"role": "...", "output": "...", "summary_json": {...}}
```

每个 RoleSubAgent 独立执行，互不通信。PM Planner 通过 `plan` JSON 分配任务，调度器并发调用各角色，然后 `merge_role_summaries()` 按字段归属规则合并输出。

#### 3.1.3 轮次收敛策略

```
R1:  主干 (3-5 个根模块, 调全部 10 角色)
R2:  枝干 (1-2 个新模块, 广度优先)
R3:  枝干 — 继续展开
R4:  枝干 — 最后展开
R5:  final_output — 解决所有 pending + 输出 PRD

进度曲线:
  早期 (0-40%): 保守。砍>延。安全基线最小化。
  中期 (40-70%): 深化。逐步引入审计/限流/降级。
  后期 (70-100%): 加强。回头加强已有模块，不新开主干。
```

### 3.2 架构设计子系统

#### 3.2.1 5 步流水线设计

```
PRD (markdown)
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 0: plan_tree (scene_tree.md skill)                       │
│   输入: PRD 全文 + §7 计数目标                                 │
│   产出: _scene_tree.md                                        │
│   内容: §1 全局摘要 §2 模块矩阵 §3 数据实体地图                  │
│         §4 页面导航 §5 鉴权需求 §6 基础设施清单                 │
│         §7 覆盖计数表 §8 全局决策记录                           │
│   策略: 自上而下，max_iter=4                                   │
└──────────────────────────────────────────────────────────────┘
    │ plan_tree (唯一基准)
    ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 1: data 层 (data.md skill)                               │
│   输入: plan_tree                                             │
│   产出: _contracts_data.json (model + auth)                   │
│   特点: 无契约依赖 — 自下而上第1层                              │
│   产出: model 契约 (tableName/fields/indexes/foreignKeys/seed) │
│         auth 契约 (tokenConfig/endpoints/middleware)           │
└──────────────────────────────────────────────────────────────┘
    │ data 契约
    ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: interfaces 层 (interfaces.md skill)                   │
│   输入: plan_tree + data 契约                                 │
│   子步骤(并发):                                                │
│     2a: api 契约 (HTTP 接口 — method/path/request/response)    │
│     2b: db-api 契约 (数据库 CRUD — operation/table/io)         │
│     2c: navigation 契约 (页面跳转 — fromPage/toPage/passBy)    │
│   每子步 max_iter=1 (输出量可控，一次到位)                      │
└──────────────────────────────────────────────────────────────┘
    │ data + interfaces 契约
    ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 3: business 层 (business.md skill)                       │
│   输入: plan_tree + data + interfaces                         │
│   产出: _contracts_business.json (scenario + logic)            │
│   特点: 依赖全部前序层                                         │
│   scenario: 业务流程编排 (chain/priority/finalState)           │
│   logic: 业务逻辑 (serviceSignature/input/output/process/      │
│          transactionBoundary/apiMapping/dbApiMapping/nfr)     │
└──────────────────────────────────────────────────────────────┘
    │ 全部 7 类契约
    ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 4: tasks 层 (tasks.md skill)                             │
│   输入: plan_tree + 全部契约 ID 清单 + 计数目标                 │
│   产出: _tasks.json (5 类任务 + 显式依赖链)                     │
│   任务类型: infra / db / frontend / backend / integration      │
│   每个任务: taskId/type/dependencies/outputFiles/usesContracts │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 5: 合并验证                                               │
│   合并全部契约 → 按类型分组 → 防御性校验                           │
│   model ≥ 实体数, api > 0, db-api > 0, navigation > 0,         │
│   scenario > 0, logic > 0, tasks ≥ 预期数                       │
│   输出: task_{timestamp}.json                                  │
└──────────────────────────────────────────────────────────────┘
```

#### 3.2.2 契约体系设计

7 类契约构成完整的设计规约，覆盖从数据到业务流程的全部层次：

```
┌──────────────────────────────────────────┐
│         business 层 (编排层)              │
│  ┌────────────┐  ┌────────────────────┐  │
│  │  scenario  │  │      logic         │  │
│  │ 业务流程编排│  │  业务逻辑(事务边界) │  │
│  │ chain/     │  │  serviceSignature  │  │
│  │ priority/  │  │  /input/output/    │  │
│  │ finalState │  │  process/nfr       │  │
│  └─────┬──────┘  └────────┬───────────┘  │
│        │ 编排              │ 调用          │
├────────┼───────────────────┼───────────────┤
│        ▼                   ▼              │
│  ┌──────────────────────────────────────┐ │
│  │         interfaces 层 (接口层)        │ │
│  │  ┌────────┐ ┌────────┐ ┌──────────┐ │ │
│  │  │  api   │ │ db-api │ │navigation│ │ │
│  │  │HTTP接口│ │CRUD操作│ │ 页面跳转  │ │ │
│  │  └────────┘ └────────┘ └──────────┘ │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  ┌──────────────────────────────────────┐ │
│  │           data 层 (基础层)            │ │
│  │  ┌────────────┐  ┌────────────────┐  │ │
│  │  │   model    │  │     auth       │  │ │
│  │  │ 数据表结构  │  │  认证配置      │  │ │
│  │  │ tableName/ │  │  JWT策略/      │  │ │
│  │  │ fields/    │  │  端点/中间件    │  │ │
│  │  │ indexes/FK │  │                │  │ │
│  │  └────────────┘  └────────────────┘  │ │
│  └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

#### 3.2.3 关键算法：自动展开嵌套包裹

Model 有时在 `interfaces` 输出中多一层嵌套（如 `{navigations: [{type: "navigation", ...}]}`），通过 `_flatten_contract_items()` 自动展开：

```python
# agent/architect.py
def _flatten_contract_items(items: list) -> list:
    known_wrappers = {"navigations", "apis", "db_apis", "db-api",
                      "models", "auths", "contracts"}
    for item in items:
        if isinstance(item, dict):
            keys = list(item.keys())
            if len(keys) == 1 and keys[0] in known_wrappers:
                inner = item[keys[0]]
                if isinstance(inner, list):
                    flat.extend(_flatten_contract_items(inner))  # 递归展开
```

### 3.3 代码生成子系统

#### 3.3.1 分层并发执行模型

```
task.json {contracts: {...}, tasks: [...]}
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  build_engineer_layers(tasks)                             │
│  1. 拓扑排序计算每个任务的深度 (BFS 迭代至收敛)             │
│  2. 按 (类型优先级, 深度) 全局排序                         │
│  3. 相邻同类型无内部依赖 → 合并为一层                      │
│                                                          │
│  输出: [[{infra tasks}], [{db tasks}],                    │
│         [{frontend tasks}], [{backend tasks}],            │
│         [{integration task}]]                             │
└──────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  逐层执行 (for each layer):                               │
│  1. 剪枝: 上游失败/剪枝 → 本层依赖该上游的任务被剪枝        │
│  2. 并发: asyncio.gather(*[execute_task(t) for t in runnable]) │
│  3. 真理: 成功后持久化到 Memory/truths/engineer/           │
│                                                          │
│  层间串行 (保证依赖) | 层内并行 (最大化效率)               │
└──────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  Integration (最后执行):                                  │
│  1. Python 预生成 init-db.js + seed-users.js + 占位图     │
│  2. Agent 执行: 路由注册 + env 配置 + Vite 构建 + DB 初始化 │
│  3. 后处理: 自动注入缺失路由 + 展开多路由 + 清理死路由      │
│           + env 补全 + 部署清单                            │
└──────────────────────────────────────────────────────────┘
```

#### 3.3.2 BaseDesigner 设计

`BaseDesigner` 是所有工程师 Agent 的基类，封装了 Agent 创建、流处理、工具包装、真理提取等公共逻辑：

```python
# agent/base_designer.py — 核心流程
class BaseDesigner:
    async def run(self, task, workspace_root, relevant_contracts, extra_instructions):
        # 1. 构建工具: create_files + edit_files + search_rag + search_code
        #    带白名单校验 + 调用次数限制(≤2次) + Step 1 窗口锁

        # 2. 组装 System Prompt (通过 prompt_builder):
        #    共享 skill → 专属 skill → 场景树 → UI 文档 → 上游真理

        # 3. 组装 User Prompt (动态, 每 task 不同):
        #    任务 JSON + 关联契约 + 真理模板

        # 4. 创建 Agent (max_iterations=6~7)

        # 5. 流式执行 + Token 追踪

        # 6. 提取真理 JSON → 保存到 Memory/truths/engineer/

        # 7. 校验: 真理文件存在 + outputFiles 存在且非空
        return {"task_id": tid, "success": True/False, ...}
```

#### 3.3.3 工具调用控制

```
工程师 Agent 的执行流程 (skill/code/workflow.md):

Step 1 — 搜集 (可选, 进入 Step 2 后不可再调)
  ├── search_rag()     ← 必须与 search_code 在同一次响应中并行调用
  ├── search_code()    ← 合计只能调 1 次
  └── 判断: 契约信息完整 → 跳过 Step 1，直接 Step 2

Step 2 — 创建 (必须)
  └── create_files()   ← 一次性传入所有 outputFiles，1 次调用

Step 3 — 修复 (按需, 最多 2 次)
  ├── edit_files() 或 create_files()  ← 修 1 次就够
  └── 合计 create+edit ≥ 3 次 → 框架拒绝

Step 4 — 真理 (必须)
  └── 输出真理 JSON → 隐含
```

**死循环防护机制**：
- 纯文本无工具调用 → 框架终止 Agent
- 同一工具连续失败 2 次 → 放弃该工具
- `🛑_NEXT` 字段是权威下一步指令
- 修过 2 次后忽略 `🛑_NEXT` 的"继续修"指令

#### 3.3.4 真理传递机制

```
工程师 A (backend, t_order_01) 完成任务
    │
    ▼ 输出真理 JSON
┌─────────────────────────────────────────┐
│ Memory/truths/engineer/t_order_01.json   │
│ {                                        │
│   "task_id": "t_order_01",               │
│   "type": "backend",                     │
│   "exposed": {                           │
│     "exposed_to_upper": {                │ ← 下游 Agent 可见
│       "POST /api/orders": {              │
│         "handler": "createOrder",        │
│         "request": {...},                │
│         "response": {...}                │
│       }                                  │
│     },                                   │
│     "exposed_to_peers": {                │ ← 同层 Agent 可见
│       "createOrder(req, res)": {...}     │
│     }                                    │
│   }                                      │
│ }                                        │
└─────────────────────────────────────────┘

下游 Agent (frontend, t_order_page_01) 通过 prompt_builder 加载:
  _load_upstream_truths("frontend", task=t_order_page_01)
  → 只加载 task.dependencies 中声明的上游真理
  → 下层真理 → exposed_to_upper
  → 同层真理 → exposed_to_peers
```

#### 3.3.5 集成验证体系

集成 Agent (`integrator.py`) 执行多层次的验证：

```
预扫描 (pre-scan, Python 确定性检查):
  ├── require/import 路径断裂检测
  ├── package.json scripts → 文件存在性
  ├── app.js 路由引用 → 文件存在性
  ├── npm 依赖完整性 (package.json deps vs require() 调用)
  └── 全链加载测试 (node -e "require('./app')" 不崩溃)

Agent 执行:
  ├── 路由注册 + 中间件挂载
  ├── .env 配置 (代码扫描 process.env.X → 根配置交叉 → 填值)
  ├── Vite 构建
  └── DB 初始化 (DDL + 种子数据)

后处理 (Python 自动修复):
  ├── 自动注入缺失路由
  ├── 展开多路由导出 (module.exports = {r1, r2} → 分别 app.use)
  ├── 清理不存在文件的 require
  ├── 死路由注释 (router/index.js 中指向不存在 .vue 的懒加载)
  ├── env 变量补全 (代码 scan → 缺失变量 → .env 追加)
  └── 四文件同步 (.env → .env.example/.development/.production)
```

### 3.4 测试修复子系统

#### 3.4.1 测试架构分层

```
test_architect.py 流水线 (与架构师相同的分层模式):

Step 0: test_plan_tree (从上往下全量规划)
    → work/project/test/_test_plan_tree.md

Step 1: 静态层 (static.md skill)
    → _test_static.md.json
    层: infra / db / frontend / peer_deps / integ
    特点: 无 testScenarios，用 checkPoints 数组代替

Step 2: 接口层 (interface.md skill)
    → _test_interface_{auth,api,dbapi,nav}.json (4 步子步)
    层: auth / db_api / api / navigation

Step 3: 逻辑层 (logic.md skill)
    → _test_logic.json
    层: backend_proc / logic / scenario
    scenario 无 sourceTask，targetFiles = 全部依赖的并集

Step 4: 质量层 (quality.md skill)
    → _test_quality.json
    层: nfr (k6 性能测试)

Step 5: 合并
    → test_tasks_{ts}.json
    去重 + 插入 t_repair_failed 硬编码占位任务
```

#### 3.4.2 ABCD 循环机制

```
┌──────────────────────────────────────────────────────────────┐
│                   ABCD 循环 (多轮迭代收敛)                     │
│                                                              │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌───────┐ │
│   │    A    │────▶│    B    │────▶│    C    │────▶│   D   │ │
│   │test     │     │test     │     │source   │     │test   │ │
│   │writer   │     │runner   │     │fixer    │     │runner │ │
│   │写测试代码│     │跑测试   │     │修复源码  │     │验证   │ │
│   │         │     │诊断失败  │     │定点修复  │     │通过→真理│ │
│   │         │     │输出 ban │     │         │     │失败→ban│ │
│   └─────────┘     └─────────┘     └─────────┘     └───────┘ │
│                                                              │
│   Ban 记忆持久化:                                             │
│   Memory/test_failure/{id}.json   ← B→A (测试自身的修复)      │
│   Memory/source_failure/{id}.json ← B→C, D→C (源码修复)      │
│                                                              │
│   收敛终点: 全部 test_tasks 通过 + test_success && source_success │
└──────────────────────────────────────────────────────────────┘
```

#### 3.4.3 B/D 诊断 Agent 设计

```
test_runner.py (B 步骤 / D 步骤):

B 步骤 — 诊断测试失败:
  1. 跑测试 → 解析失败详情
  2. 从错误堆栈提取源文件:行号
  3. 加载 B 角色 skill (skill/test/diagnosis/b/{testType}/{layer}.md)
  4. 请求源码上下文 → Agent 诊断
  5. 调用 load_d_card() → 加载 D 角色知识 (判断 fix_target=test/source)
  6. 输出 <!--FINAL--> ban JSON (f=指纹 | b=修复指令)

D 步骤 — 验证修复:
  1. 接收 C 修改后的源码
  2. 重新跑测试
  3. 变更分析 → 对照验收 → 回归扫描 → 意图分析
  4. 通过 → 输出真理 JSON，失败 → 输出新 ban
```

#### 3.4.4 Ban 指纹格式

```
Ban 格式 (f=指纹 | b=修复指令):

f = layer | fix_target | file:line | SUBTYPE

字段说明:
  layer:      infra/db/frontend/auth/db_api/api/navigation/
              backend_proc/logic/scenario/nfr
  fix_target: test (修测试文件) 或 source (修源码文件)
  file:       文件路径:行号
  SUBTYPE:    WRONG_COLUMN / SYNTAX / MOCK_GAP / MISSING_EXPORT /
              WRONG_FORMAT / MISSING_ROLLBACK / CHEAT / ...

示例:
  f=backend_proc|source|controllers/orderController.js:45|WRONG_COLUMN
  b=DON'T: 用 order.userId 查询 | fix: 改用 order.user_id (model 契约字段名)
     | target=source

  f=auth|test|test/t_auth_001.test.js:20|MOCK_GAP
  b=DON'T: mock jwt.verify 返回 null | fix: mock 返回 {userId: 1, role: 'user'}
     | target=test
```

#### 3.4.5 静态层直通模式

静态层（infra/db/frontend/peer_deps/integ）跳过 ABCD 循环，采用直通模式：

```
┌─────────────────────────────────────────────────────────────┐
│  静态层执行流程 (source_fixer.py, is_static=True)             │
│                                                             │
│  1. Python 全量静态检查 (_run_full_static_check)              │
│     ├── 语法检查 (node --check / esbuild)                    │
│     ├── CJS 禁止检查 (src/ 下禁止 require/module.exports)    │
│     ├── 导出分析 (实际导出 vs checkPoints)                    │
│     ├── checkPoints 逐条对照                                  │
│     ├── DDL vs 契约对比 (表名/字段/类型/约束/索引/FK)         │
│     ├── 种子数据检查 (JSON 有效性/列名对齐/FK 引用一致性)     │
│     ├── CJS require 链断裂检查 + 循环依赖检测                 │
│     ├── npm 依赖完整性检查                                    │
│     ├── 死路由检查 + 前端路由组件完整性                         │
│     ├── 路由注册双向验证 (app.js → routes/ + routes/ → app.js)│
│     ├── UI 色板检查 (vs Memory/ui_styles/ 动态色板)           │
│     ├── Vite 构建检查 (按任务文件范围)                         │
│     ├── 全链加载测试 (node app.js)                            │
│     └── 端点覆盖检查 (route vs 前端 API 模块)                  │
│                                                             │
│  2. Agent 修复 (max_iterations=6)                             │
│     工具: scan_services + read_files + edit_batch + create   │
│           + search_rag + search_code + verify_checkpoints    │
│     限制: edit/create 合计 1 次                                │
│                                                             │
│  3. verify_checkpoints() — Python 自检全部 checkPoints       │
│     通过 → 输出真理 | 失败 → 输出 ban                        │
│                                                             │
│  4. Ban 存入 Memory (跨 attempt 记忆持久化)                    │
└─────────────────────────────────────────────────────────────┘
```

#### 3.4.6 双层屏障并发控制

```
同一 testType 内同层任务并发执行，通过双层屏障控制跨步同步：

屏障 1 (C→D 解锁):
  条件: b_p + s_o + s_f + skipped >= total
  含义: 全部 B/C/smoke/skip 完成后，运行 D 验证的任务进入 D 步骤

屏障 2 (D→下轮解锁):
  条件: d_p + d_f >= s_o
  含义: 全部 D 完成后，进入下一轮迭代

状态变量:
  total:  本轮参与 barrier 的任务总数
  b_p:    B 测试全部通过 (无需 C/D, 直接 done)
  s_o:    C 完成 + smoke 通过 (进入 D)
  s_f:    C 完成 + smoke 失败 (回滚, 不参与 D)
  skipped: B test ban / C fixer fail 等跳过的
  d_p:    D 验证通过
  d_f:    D 验证失败

全局状态重置: _round_done >= total 且 d_p + d_f >= s_o
  → total=0, 新 Events, 新 _registered_tasks
```

---

## 第四章：知识管理系统

### 4.1 技能系统 (Skill)

121 个 Markdown 文件构成分层知识体系，是 Agent 的"领域知识"来源：

```
skill/
├── design/           # 需求分析角色技能 (11 文件)
│   ├── product_manager.md  # PM 任务规划师 — 核心编排技能
│   ├── customer.md         # 客户视角 — 商业价值/ROI
│   ├── user.md             # 用户视角 — 前台功能/痛点
│   ├── manager.md          # 运营视角 — 后台管理/数据看板
│   ├── innovator.md        # 创新视角 — 差异化/技术可行创新
│   ├── business.md         # 行业专家 — 标准功能模板/偏差预警
│   ├── qa.md               # 质量视角 — 边界场景/回归风险
│   ├── data.md             # 数据视角 — 实体/约束/状态机
│   ├── architect.md        # 架构视角 — 成本/基础设施/降级
│   ├── security.md         # 安全视角 — 加密/Token/脱敏/合规
│   └── designer.md         # 设计视角 — CSS 变量/组件风格
│
├── engineer/         # 工程技能 (12 文件)
│   ├── architect/         # 架构师技能
│   │   ├── common.md           # 通用编码规范
│   │   ├── scene_tree.md       # 场景树生成规则
│   │   ├── data.md             # 数据层契约规则
│   │   ├── interfaces.md       # 接口层契约规则
│   │   ├── business.md         # 业务层契约规则
│   │   └── tasks.md            # 任务分配规则
│   └── code_generation/   # 代码生成技能
│       ├── infrastructure.md   # 基础设施工程师
│       ├── database.md         # 数据库设计师
│       ├── backend.md          # 后端开发工程师
│       ├── frontend.md         # 前端开发工程师
│       └── integrator.md       # 集成工程师
│
├── test/             # 测试技能 (100+ 文件)
│   ├── architect/         # 测试架构师技能
│   │   ├── common.md / static.md / interface.md / logic.md / quality.md
│   ├── roles/a/           # A 步骤 (测试编写) — 按 testType/layer 分组
│   │   ├── {testType}.md         # 通用角色
│   │   └── {testType}/{layer}.md # 子层特化
│   ├── diagnosis/b/       # B 步骤 (测试诊断) — 同上分组
│   ├── diagnosis/d/       # D 步骤 (修复验证) — 同上分组
│   ├── roles/c/           # C 步骤 (源码修复) — 同上分组
│   ├── repair/            # 修复策略
│   │   ├── a/{testType}/{layer}.md  # A 修复策略
│   │   └── c/{testType}.md         # C 修复策略
│   ├── templates/         # 测试模板
│   │   └── {testType}/{layer}.md   # 按类型分层
│   └── truths/            # 真理格式定义
│       └── {layer}.md            # 每层真理的 JSON Schema
│
├── code/             # 代码规范 (3 文件)
│   ├── quality.md         # 通用代码质量规范 (所有 Agent 共享)
│   ├── readability.md     # 代码可读性规范 (所有 Agent 共享)
│   └── workflow.md        # 工具调用与执行流程 (所有 Agent 共享)
│
└── rag/              # RAG 技能 (3 文件)
    ├── retrieval_skill.md  # 检索路由技能
    └── build/              # 知识库构建
        ├── refine.md        # 经验净化
        └── merge.md         # 语义合并
```

**技能加载策略**：

```python
# agent/prompt_builder.py — System Prompt 组装顺序

# ═══ 第 1 段: 5 种 Agent 完全共享 ═══ (缓存命中)
quality.md       → "## 通用代码质量规范"
readability.md   → "## 代码可读性规范"
workflow.md      → "## 🛑 工具调用与执行流程"
_scene_tree.md   → "## 🛑 场景树"

# ═══ 第 2 段: 某类型专属 ═══
# 前端:
_global.md + _components.md → "## 🎨 全局 UI 设计规范"
task.ui_style → 对应的 Memory/ui_styles/{name}.md → "## 🎨 本任务专属 UI 风格"

# 所有:
agent_type skill (infra/db/backend/frontend/integration).md

# ═══ 第 3 段: 本任务专属 ═══
_load_upstream_truths() → 上游真理 (仅直接依赖)
extra_instructions      → 环境约束等

# 测试 Agent (scheduler 组装):
# role + template + repair → 动态组合:
#   skill/test/roles/{step}/{testType}.md
#   + skill/test/roles/{step}/{testType}/{layer}.md
```

### 4.2 localAgent 子系统 — 本地 LLM Agent 调用器

`localAgent/` 包含两个轻量级 Agent 调用器，专为 RAG 知识库的 **LLM 净化** 和 **检索交付** 任务设计。它们不参与主代码生成流程，而是作为 RAG 流水线的"智能处理单元"。

#### 4.2.1 设计定位

```
┌────────────────────────────────────────────────────────────┐
│                  localAgent 在系统中的位置                   │
│                                                            │
│  brainAgent/knowledge_builder.py                           │
│    │  知识库构建调度器 (Python 硬编码流程)                    │
│    │                                                       │
│    ├──→ localAgent/knowledge_builder.py                    │
│    │      └── run_knowledge_builder("refine", data)        │
│    │           Step 3: LLM 经验净化 (去噪+结构化)            │
│    │           Step 4: LLM 语义合并 (冲突消解)               │
│    │                                                       │
│  brainAgent/retrieval_scheduler.py                         │
│    │  检索调度器 (Python 硬编码流程)                         │
│    │                                                       │
│    └──→ localAgent/retrieval_agent.py                      │
│           ├── run_retrieval_agent("angle_analysis", data)  │
│           │     Step 1: 查询多角度分析                       │
│           └── run_retrieval_agent("deliver", data)         │
│                 Step 3: 检索结果格式化交付                   │
└────────────────────────────────────────────────────────────┘
```

#### 4.2.2 knowledge_builder.py — 知识构建 Agent

```python
# localAgent/knowledge_builder.py — 核心设计

# 支持两种 LLM 任务:
SKILL_PATH = {
    "refine": "skill/rag/build/refine.md",    # 经验净化 (去噪+结构化)
    "merge":  "skill/rag/build/merge.md",     # 语义合并 (冲突消解)
}

async def run_knowledge_builder(role: str, task) -> dict:
    # 1. 加载对应的 skill 文件 (Markdown)
    skill = load_skill(SKILL_PATH[role])

    # 2. 将 task 数据 JSON 序列化后注入 prompt
    instructions = f"{skill}\n\n用户的输入:\n{json.dumps(task)}"

    # 3. 创建 Agent (无工具, 纯推理, max_iterations=2)
    agent = Agent(name=f"knowledge_builder_{role}",
                  instructions=instructions,
                  model_client=model_client,
                  tools=[], max_iterations=2)

    # 4. 流式执行 + JSON 提取
    for event in agent.run_stream(): collected += str(event)
    return extract_json(collected)
```

**两个 LLM 任务的职责**:

| 角色 | Skill | 输入 | 输出 | 用途 |
|------|-------|------|------|------|
| `refine` | refine.md | 原始 ban 记录列表 | 结构化的经验 JSON 数组 | 去掉 LLM 输出的噪音，补全 do/dont/context/severity/category |
| `merge` | merge.md | 新旧两条相似经验 | 合并后的统一经验 JSON | 语义去重阶段 (sim≥0.85) 的冲突消解 |

#### 4.2.3 retrieval_agent.py — 检索 Agent

```python
# localAgent/retrieval_agent.py — 核心设计

# 支持两种 LLM 任务:
SKILL_PATH = {
    "angle_analysis": "skill/rag/search/angle_analysis.md",  # 查询角度分析
    "deliver":        "skill/rag/search/deliver.md",         # 结果格式化交付
}

async def run_retrieval_agent(role: str, task) -> dict:
    # 与 knowledge_builder 相同的模式:
    # 加载 skill → 注入 JSON 数据 → 创建 Agent → 流式执行 → 提取 JSON
    skill = load_skill(SKILL_PATH[role])
    agent = Agent(name=f"retrieval_{role}",
                  instructions=f"{skill}\n\n{json.dumps(task)}",
                  model_client=model_client,
                  tools=[], max_iterations=2)
    return extract_json(collected)
```

**两个 LLM 任务的职责**:

| 角色 | Skill | 输入 | 输出 | 用途 |
|------|-------|------|------|------|
| `angle_analysis` | angle_analysis.md | {query, task_id, agent_type} | {angles: [{id, name, query}]} | 将用户自然语言查询拆解为 3 个多角度检索查询 |
| `deliver` | deliver.md | {results, angles, agent_type, ...} | {summary, delivery, suggestions} | 将去重后的检索结果格式化为目标 Agent 类型可直接消费的内容 |

#### 4.2.4 设计模式总结

localAgent 的两个模块采用完全相同的设计模式：

```
┌─────────────────────────────────────────┐
│         localAgent 通用调用模式          │
│                                         │
│  1. 加载 Skill (Markdown 角色定义)       │
│  2. 序列化 task → JSON 注入 prompt       │
│  3. 创建 picoagents Agent               │
│     - instructions = skill + task_data  │
│     - tools = [] (纯推理, 无工具调用)    │
│     - max_iterations = 2               │
│  4. 流式执行 agent.run_stream()         │
│  5. extract_json(collected) 提取结果    │
│  6. 多层回退: JSON 解析失败 → 返回 error │
└─────────────────────────────────────────┘
```

这种设计将 LLM 调用封装为**纯函数式接口**：输入 JSON → LLM 推理 → 输出 JSON。Python 调度器 (knowledge_builder / retrieval_scheduler) 负责硬编码流程控制，只在需要"智能判断"的节点调用 localAgent。

---

### 4.3 RAG 知识库

#### 4.3.1 完整架构

```
┌──────────────────────────────────────────────────────────────────┐
│                       RAG 知识库完整架构                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              知识构建流水线 (brainAgent/knowledge_builder)    │  │
│  │                                                            │  │
│  │  Step 0: 文件发现                                           │  │
│  │    list_files("Memory/test_failure,Memory/source_failure,   │  │
│  │                work/project/test,work/project/task")        │  │
│  │    classify_files() → memory_files + task_files + source    │  │
│  │                                                            │  │
│  │  Step 1: 记忆清洗                                           │  │
│  │    filter_memory(bans) — Python 硬编码:                     │  │
│  │      保留: f 以 L3|/L4|/L5| 开头 (旧格式高价值)             │  │
│  │      保留: f 第2段为 test_writer/source (新格式)             │  │
│  │      丢弃: actor=scheduler 的记忆 (环境问题不持久化)          │  │
│  │                                                            │  │
│  │  Step 2: 锚点绑定 (build_anchor_mapping)                    │  │
│  │    Python 硬编码 — 建立 ban → test_task → dev_task →        │  │
│  │    contracts 的关联链:                                      │  │
│  │    1. ban.source_file 提取 test_id                          │  │
│  │    2. test_task.targetFiles 匹配 dev_task.outputFiles       │  │
│  │    3. dev_task.requiredContracts → trigger_contracts        │  │
│  │    4. 递归遍历 dependencies 链 (扩大匹配范围)                 │  │
│  │    5. 生成 trigger_tags (memory_test/memory_source/smoke)   │  │
│  │                                                            │  │
│  │  Step 3: LLM 净化 (localAgent/knowledge_builder)            │  │
│  │    → run_knowledge_builder("refine", anchored_records)      │  │
│  │    LLM 对每条 ban 做:                                        │  │
│  │    - 提取 do (正确做法) / dont (错误做法) / context (场景)    │  │
│  │    - 分类: category (logic_pitfall/db_ops/api_design/...)   │  │
│  │    - 评级: severity (high/medium/low)                       │  │
│  │    - 补全: entity_refs (涉及的实体)                           │  │
│  │    降级: LLM 失败 → 用原始 ban_text 构造 fallback 记录        │  │
│  │                                                            │  │
│  │  Step 4: 去重与合并 (Python + LLM 混合)                      │  │
│  │    dedup_by_fingerprint() — Python 精确去重:                 │  │
│  │      同 source_fingerprint → 内容相同跳过 / 不同更新         │  │
│  │    semantic_dedup() — Python 语义去重:                       │  │
│  │      向量相似度 ≥ 0.95 → 直接跳过                            │  │
│  │      向量相似度 0.85~0.95 → review_items → LLM merge         │  │
│  │    → run_knowledge_builder("merge", {new, similar})          │  │
│  │      LLM 将两条高度相似的经验合并为一条                        │  │
│  │                                                            │  │
│  │  Step 5: 向量化并存储                                        │  │
│  │    embed_text_batch(texts) — sentence-transformers 批量嵌入  │  │
│  │    build_embedding_text(rec) — 构造向量文本:                  │  │
│  │      do + dont + context + trigger_contracts +               │  │
│  │      trigger_tasks + trigger_tags                           │  │
│  │    table.merge_insert(on="id") → LanceDB                    │  │
│  │                                                            │  │
│  │  Step 6: 创建索引                                            │  │
│  │    标量索引: source_fingerprint / category / severity (BTREE) │  │
│  │    向量索引: vector 列 (IVF_PQ, >=256 条时创建)              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │               存储层 (LanceDB)                               │  │
│  │                                                            │  │
│  │  数据库: knowledge/ (本地磁盘)                                │  │
│  │  表: knowledge_base (构建中间表, 含完整向量)                   │  │
│  │       knowledge (聚类后检索表, 可选)                          │  │
│  │                                                            │  │
│  │  Schema (knowledge_base):                                   │  │
│  │    id: string                    ← exp_{uuid16}             │  │
│  │    source_fingerprint: string    ← ban 指纹 (唯一锚点)       │  │
│  │    do: string                    ← 正确做法                  │  │
│  │    dont: string                  ← 错误做法                  │  │
│  │    context: string               ← 场景说明                  │  │
│  │    trigger_tasks: list[string]   ← 关联的任务 ID             │  │
│  │    trigger_contracts: list[str]  ← 关联的契约 ID             │  │
│  │    trigger_tags: list[string]    ← memory_test/source/smoke │  │
│  │    entity_refs: list[string]     ← 涉及的实体名              │  │
│  │    severity: string              ← high/medium/low          │  │
│  │    category: string              ← 经验分类                  │  │
│  │    source_files: list[string]    ← 来源文件路径              │  │
│  │    version: int32                ← 版本号 (更新次数)         │  │
│  │    vector: list[float32]         ← embedding 向量            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          检索调度层 (brainAgent/retrieval_scheduler)          │  │
│  │                                                            │  │
│  │  retrieval_scheduler(task_id, query, agent_type):           │  │
│  │                                                            │  │
│  │  Step 1: 角度分析 (LLM)                                      │  │
│  │    → run_retrieval_agent("angle_analysis", {query, ...})    │  │
│  │    输入: "创建订单时如何防止库存超卖?"                         │  │
│  │    输出: [                                                  │  │
│  │      {id:"A", name:"正确实现", query:"如何正确实现..."},      │  │
│  │      {id:"B", name:"边界异常", query:"有哪些边界条件..."},    │  │
│  │      {id:"C", name:"陷阱防御", query:"有哪些常见陷阱..."}     │  │
│  │    ]                                                        │  │
│  │    降级: LLM 失败 → 硬编码 3 个默认角度                       │  │
│  │                                                            │  │
│  │  Step 2: 3×3 扩散检索 (Python 硬编码)                        │  │
│  │    for angle in angles:                                     │  │
│  │      retrieve_single_angle(task_id, angle.query, top_k=3)   │  │
│  │        → ExperienceQuery.build_lance_filter()               │  │
│  │          图约束: array_contains(trigger_contracts, anchor)   │  │
│  │          标签: memory_test OR memory_source OR smoke         │  │
│  │        → embed_text(query) → table.search(vector)           │  │
│  │        → exclude_ids 去重 (不同角度不重复返回同一条)          │  │
│  │        → 降级: 带合约过滤无结果 → 仅标签过滤重试              │  │
│  │    deduplicate_results(all, min_similarity=0.55)            │  │
│  │                                                            │  │
│  │  Step 3: 结果交付 (LLM)                                      │  │
│  │    → run_retrieval_agent("deliver", {results, angles, ...}) │  │
│  │    输出: {summary, delivery, suggestions}                   │  │
│  │    delivery 按 agent_type 格式化:                            │  │
│  │      code_generator → prompt_injection 文本                 │  │
│  │      test_generator → prompt_injection 文本                 │  │
│  │      test_repair    → structured JSON                      │  │
│  │      architect      → structured JSON                      │  │
│  │                                                            │  │
│  │  Step 4: 缓存写入 (Redis, 可选)                              │  │
│  │    cache_key = md5(normalized_query|agent_type|top_k)       │  │
│  │    redis.set(cache_key, json.dumps(result), ex=86400)       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Agent 工具接口层                                │  │
│  │                                                            │  │
│  │  search_rag(query)  — RAG 经验检索                          │  │
│  │    → retrieval_scheduler(task_id, query, agent_type)       │  │
│  │    → 返回 {ok, summary, content, results_count}            │  │
│  │    供 code_generator / test_generator / test_repair 等调用  │  │
│  │                                                            │  │
│  │  search_code(query) — 高分代码检索                           │  │
│  │    → code_retrieval.retrieve_code / retrieve_test_code     │  │
│  │    → 搜索 S/A 级参考实现 (评分≥85)                           │  │
│  │    供 code_generator / test_writer 等调用                   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.3.2 图锚点缓存机制

```python
# Tools/rag/build/tools.py — 图锚点缓存

# 构建时: 从 task.json 加载全部任务 → 建立索引
_anchor_cache: Dict[str, List[str]] = {}    # task_id → [contract_id, ...]
_task_graph: Dict[str, dict] = {}           # task_id → {contracts, dependencies}

def load_anchor_cache_from_tasks(task_dir: Path):
    for f in task_dir.glob("task_*.json"):
        for task in data["tasks"]:
            _anchor_cache[tid] = task["requiredContracts"]
            _task_graph[tid] = {"contracts": ..., "dependencies": [...]}

# 检索时: ExperienceQuery 根据 task_id 查关联契约 → 构建 LanceDB filter
class ExperienceQuery:
    def build_lance_filter(self) -> str:
        anchors = get_anchors_from_task_id(self.task_id, expand_deps=1)
        # array_contains(trigger_contracts, 'C_order') OR
        # array_contains(trigger_contracts, 'C_payment') ...
        # AND (memory_test OR memory_source OR smoke)

    def get_anchors_for_task(self) -> List[str]:
        # 展开至直接依赖 (expand_deps=1):
        #   当前 task 的 contracts + 所有直接依赖 task 的 contracts
        # 确保检索时覆盖上下游关联契约的经验
```

#### 4.3.3 向量文本构造策略

```python
# Tools/rag/build/tools.py — build_embedding_text()

def build_embedding_text(record: dict) -> str:
    """
    构造用于向量化的文本。设计原则:

    加入 (核心语义):
      - do (正确做法) — 自然语言，LLM 查询对齐
      - dont (错误做法) — 自然语言，LLM 查询对齐
      - context (场景说明) — 自然语言，LLM 查询对齐

    加入 (结构化锚点):
      - trigger_contracts 全部 — 业务锚点
      - trigger_tasks — 任务上下文
      - trigger_tags — 标签辅助信号 (smoke/memory_test 等)

    不加入:
      - source_fingerprint — 机器生成的领域黑话，稀释语义
      - category — 单字技术代码，不与自然语言查询对齐
    """
    parts = []
    if record.get("do"):    parts.append(record["do"])
    if record.get("dont"):  parts.append(record["dont"])
    if record.get("context"): parts.append(record["context"])
    contracts = record.get("trigger_contracts", [])
    if contracts: parts.append(" ".join(contracts))
    tasks = record.get("trigger_tasks", [])
    if tasks: parts.append(" ".join(tasks))
    tags = record.get("trigger_tags", [])
    if tags: parts.append(" ".join(tags))
    return " ".join(parts)
```

#### 4.3.4 记忆生命周期

```
Agent 执行失败
    │
    ▼
B/D 步骤输出 ban
    │
    ├──→ Memory/test_failure/{taskId}.json   (测试问题)
    └──→ Memory/source_failure/{taskId}.json (源码问题)
    │
    ▼
每轮末 _cleanup_round_failures()
    ├── passed 任务的 ban → 保留 (有效经验)
    └── failed 任务的 ban → 删除 (无效经验, 下轮重新诊断)
    │
    ▼
knowledge_builder 定时/按需运行
    ├── Step 0: 文件发现 (list_files 硬编码目录)
    ├── Step 1: 过滤 (Python: L3+|test_writer|source 保留)
    ├── Step 2: 锚点绑定 (Python: ban→test_task→dev_task→contracts)
    ├── Step 3: LLM 净化 (localAgent: refine, 去噪+结构化)
    ├── Step 4: 去重 (Python: fingerprint exact + semantic)
    │           + LLM merge (localAgent: 冲突消解)
    ├── Step 5: 向量化 (sentence-transformers batch embed)
    └── Step 6: 索引 (IVF_PQ on LanceDB)
    │
    ▼
Agent 通过 search_rag(query) / search_code(query) 检索
    → retrieval_scheduler → 角度分析(LLM) → 3×3检索 → 交付格式化(LLM)
    → Redis 缓存 (24h TTL, 同义查询命中)
```

#### 4.3.5 检索缓存策略

```python
# brainAgent/retrieval_scheduler.py — Redis 缓存

def _cache_key(query, agent_type, top_k, min_similarity) -> str:
    # 规范化 query → md5 → 16 位 hex
    norm = query.strip().lower()[:200]
    fingerprint = md5(f"{norm}|{agent_type}|{top_k}|{min_similarity:.2f}")
    return f"rag_cache:{fingerprint}"

# 检索流程:
# 1. 检查 Redis → 命中直接返回 (跳过 LLM 角度分析+交付)
# 2. 未命中 → 完整检索 → 写入 Redis (TTL=24h)
# 3. Redis 不可用 → 降级为无缓存模式 (不报错)
```

#### 4.3.6 代码检索 (search_code)

```python
# Tools/rag/search_code.py — 双路由代码检索

def make_search_code(task_id, agent_type):
    _is_test = agent_type in ("test_writer", "test_generator")

    async def search_code(query: str) -> dict:
        if _is_test:
            # 查测试代码库 → 找高分测试参考 (≥85 分)
            results = await retrieve_test_code(task_id, query,
                            top_k=3, min_test_score=85)
        else:
            # 查源码库 → 找高分实现参考 (≥85 分)
            results = await retrieve_code(task_id, query,
                            top_k=3, min_code_score=85)
        return {"ok": True, "results": simplified, ...}
```

与 `search_rag` (查历史经验) 不同，`search_code` 查询的是**代码评分系统**产出的高分参考实现 (S/A 级)，帮助 Agent 了解"好的代码长什么样"。

### 4.3 真理 (Truth) 管理

真理文件是 Agent 间传递接口信息的唯一机制：

```
Memory/truths/
├── engineer/              # 工程师真理 (代码生成阶段产出)
│   ├── t_infra_01.json    # infra 任务真理 (package.json 导出清单)
│   ├── t_db_users.json    # db 任务真理 (表结构+种子数据描述)
│   ├── t_backend_auth.json# backend 任务真理 (API 签名+错误码)
│   └── t_frontend_home.json # frontend 任务真理 (组件导出+路由)
│
└── test/                  # 测试真理 (ABCD 循环 D 步骤产出)
    └── t_auth_001.json    # D 验证通过后的真理
```

真理 JSON 结构：
```json
{
  "task_id": "t_backend_order_01",
  "type": "backend",
  "output_files": ["routes/orderRoutes.js", "controllers/orderController.js"],
  "description": "订单 CRUD API",
  "exposed": {
    "exposed_to_upper": {
      "POST /api/orders": {
        "handler": "createOrder",
        "auth": "authenticate",
        "request": { "body": ["productId", "quantity", "addressId"] },
        "response": { "orderId": "number", "status": "string" }
      }
    },
    "exposed_to_peers": {
      "createOrder": { "file": "controllers/orderController.js", "line": 12 }
    }
  }
}
```

---

## 第五章：工具系统设计

### 5.1 工具分层

```
┌────────────────────────────────────────────────────────────┐
│                     工具分层架构                            │
│                                                            │
│  ┌──────────────────────────────────────────────────┐     │
│  │           Agent 工具 (被 Agent 调用的 FunctionTool) │     │
│  │                                                    │     │
│  │  代码操作: create_files / edit_batch / read_file    │     │
│  │           list_files / syntax_check / quick_check   │     │
│  │  测试:     agent_run_test / npm_install             │     │
│  │  记忆:     save_memory / load_memory / ban_memory   │     │
│  │  检索:     search_rag / search_code                │     │
│  │  技能:     load_skill                              │     │
│  └──────────────────────────────────────────────────┘     │
│                                                            │
│  ┌──────────────────────────────────────────────────┐     │
│  │         Python 调度工具 (被 scheduler 调用)         │     │
│  │                                                    │     │
│  │  DDL vs 契约对比 / 种子数据检查 / CJS 链检查         │     │
│  │  npm 依赖检查 / Vite 构建检查 / 死路由检查           │     │
│  │  端点覆盖检查 / UI 色板检查 / 路由注册验证            │     │
│  │  全链加载测试 / 循环依赖检测                         │     │
│  └──────────────────────────────────────────────────┘     │
│                                                            │
│  ┌──────────────────────────────────────────────────┐     │
│  │           基础设施工具 (被各层共用)                  │     │
│  │                                                    │     │
│  │  model_client (LLM 客户端单例)                      │     │
│  │  token_tracker (Token 消耗追踪)                     │     │
│  │  dependency_graph (DAG 分层)                        │     │
│  │  json_extractor (JSON 解析)                         │     │
│  │  logger (统一日志)                                   │     │
│  └──────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────┘
```

### 5.2 工具包装器模式

所有 Agent 工具通过工厂函数创建，实现**白名单校验 + 次数限制 + 状态锁**：

```python
# agent/base_designer.py — 工具包装模式

def _make_create_files_wrapper(target_files, abs_workspace, workspace_path,
                                _close_step1, _file_tool_calls):
    _allowed = set(target_files)      # 白名单 — 只能创建 outputFiles
    MAX_FILE_CALLS = 2                # create + edit 合计上限

    async def create_files(files, metadata=None):
        _close_step1()                # 关闭 Step 1 (禁止 search_rag/code)
        _file_tool_calls[0] += 1      # 计数 +1

        # 白名单校验 — 禁止创建 outputFiles 之外的文件
        for f in files:
            if f["path"] not in _allowed:
                return {"error": f"禁止创建 '{f['path']}'", ...}

        result = await _create_files(files, ...)

        # 自动触发语法检查 + 完整性检查
        qc = await _quick_check(created, workspace=abs_workspace)
        result["quick_check"] = qc

        # 动态生成下一步指令
        if still_missing:
            result["🛑_NEXT"] = f"还有 {len(still_missing)} 个文件未创建 → 补建"
        elif qc_ok:
            result["🛑_NEXT"] = "全部完成！输出真理 JSON"
        else:
            result["🛑_NEXT"] = "有语法问题 → edit_files 修 1 次"
        return result

    return create_files
```

---

## 第六章：Prompt 工程设计

### 6.1 缓存优先的组装策略

```
System Prompt 固定顺序 (最大化跨 task 缓存命中):

位置 0-2:  5 种 Agent 完全共享 → 缓存命中
  quality.md + readability.md + workflow.md

位置 3-4:  某类型共享 → 同类型 task 间缓存命中
  场景树 + Agent 专属 skill

位置 5-6:  某类型内部分共享 → 部分缓存命中
  UI 风格文档 (仅前端)

位置 7:    本 task 专属 → 无缓存
  上游真理 + 环境约束

User Prompt: 全部动态 → 无缓存，但 token 量少
  任务 JSON + 关联契约 + 真理模板
```

### 6.2 Monkey-patch 兼容性修复

DeepSeek API 不兼容 JSON Schema 中的 `"description": null`，通过 monkey-patch 修复：

```python
# agent/architect.py
_orig_build_params = FunctionTool._build_parameters_schema

def _patched_build_params(self) -> dict:
    schema = _orig_build_params(self)
    for prop in schema.get("properties", {}).values():
        for key in list(prop.keys()):
            if prop[key] is None:
                del prop[key]
    return schema

FunctionTool._build_parameters_schema = _patched_build_params
```

---

## 第七章：并发与调度设计

### 7.1 并发模型

```
全局并发控制:
  MAX_CONCURRENT_TASKS = 100  (asyncio.gather 自然上限)

engineer 阶段:
  层间: 串行 (保证依赖顺序)
    Layer 0: infra ────────────→
    Layer 1: db ───────────────→
    Layer 2: frontend ─────────→
    Layer 3: backend ─────────→
    Layer 4: integration ──────→

  层内: 同类型任务并发 (asyncio.gather)
    ┌─ t_infra_01 ─┐
    ├─ t_infra_02 ─┤─── asyncio.gather ───→ 全部完成后进入下一层
    ├─ t_infra_03 ─┤
    └─ t_infra_04 ─┘

  剪枝: 上游失败 → 依赖该上游的任务直接标记为 pruned

scheduler 阶段:
  同 testType 同 layer 内并发
  ├── 静态层特例: 共享 targetFiles 的任务通过信号量控制
  └── 接口/逻辑/质量层: ABCD 循环 + 双层屏障
```

### 7.2 文件冲突处理

```
engineer 阶段文件冲突检测 (_report_file_conflicts):

同类型重叠 → ⚠️ 文件锁控制 (同层并发时通过信号量串行化)
  例: t_infra_01 和 t_infra_02 都写 package.json

跨类型重叠 → ✅ 允许 (不同层顺序执行，不会并发冲突)
  例: t_db_users 创建 database/schema/users.sql
       t_integration 读取 database/schema/users.sql 生成 init-db.js
```

### 7.3 状态持久化与恢复

```python
# brainAgent/engineer.py — 任务状态持久化
class EngineerTaskState:
    task_id: str
    success: bool
    output_files: list
    timestamp: str
    error: str

# 保存: Memory/agent_logs/engineer/states/{task_id}.json
_save_engineer_state(state)

# 恢复模式: --resume
# 1. 加载状态 → is_done=True → 验证 outputFiles 存在且非空 → 跳过
# 2. is_done=True 但文件缺失 → 清除状态 → 重新执行

# scheduler 阶段:
class TaskTestState:
    test_success: bool
    source_success: bool
    attempt: int
    done: bool
    best_score: float

# 保存: Memory/test_logs/{task_id}.json
```

---

## 第八章：Token 经济系统

### 8.1 双轨 Token 追踪

```
TokenTracker (utils/token.py) — 非侵入式旁路观测:

┌─────────────────────────────────────────────────────┐
│  API 轨道 (精确):                                    │
│  - 从 AssistantMessage.usage 提取每轮 LLM 调用的      │
│    tokens_input / tokens_output                      │
│  - AgentResponse.context.messages 提供 per-call 数据  │
│  - 增量计算避免重复累计                               │
│                                                     │
│  估算轨道 (补充):                                    │
│  - 中文字符 / 1.5 ≈ tokens                          │
│  - 英文字符 / 4 ≈ tokens                            │
│  - 覆盖 API usage 未报告的内容 (prompt 上下文)        │
└─────────────────────────────────────────────────────┘

输出: token/{category}/{timestamp}_{task_id}.json
  - summary: 总输入/输出 token + 估算费用
  - llm_calls: 每次 LLM 调用的详细消耗
  - tool_executions: 每次工具调用的结果预览
```

### 8.2 阶段级余额追踪

```python
# utils/token_tracker.py — 5 阶段余额追踪
record_stage("需求分析", phase="start")   # 阶段开始快照
record_stage("需求分析", phase="end")     # 阶段结束快照 → 自动计算 cost

# 阶段名称 (5 个):
#   需求分析 / 架构任务生成 / 源代码生成 / 测试任务生成 / 测试与修复

# 每阶段开始和结束时查询 DeepSeek 余额 API
# 阶段消耗 = start_total - end_total
# 持久化: Memory/token/{阶段名}.json (含历史序列)
```

---

## 第九章：关键数据结构

### 9.1 架构任务 (task.json)

```json
{
  "meta": {
    "generatedAt": "2026-07-17T12:00:00",
    "prdSource": "requirement_report_*.md",
    "pipeline": "plan_tree->data->interfaces->business->tasks"
  },
  "contracts": {
    "model": [{ "contractId": "M_order", "tableName": "orders", "fields": [...] }],
    "auth": [{ "contractId": "A_jwt", "tokenConfig": {...} }],
    "api": [{ "contractId": "API_order_crud", "basePath": "/api/orders", "endpoints": [...] }],
    "db-api": [{ "contractId": "DBA_order_insert", "operation": "INSERT", "tableName": "orders" }],
    "navigation": [{ "contractId": "NAV_home_to_products", "fromPageFile": "Home.vue", "toPageFile": "Products.vue" }],
    "scenario": [{ "contractId": "SCO_checkout", "chain": [...], "priority": "P0" }],
    "logic": [{ "contractId": "LOG_create_order", "serviceSignature": "async createOrder(req, res)", "process": [...], "transactionBoundary": "REQUIRED" }]
  },
  "tasks": [
    {
      "taskId": "t_infra_01",
      "type": "infra",
      "dependencies": [],
      "outputFiles": ["package.json", "config/db.js", "middleware/auth.js", ...],
      "usesContracts": [],
      "description": "项目初始化：package.json、数据库配置、JWT 中间件、日志、统一响应"
    }
  ]
}
```

### 9.2 测试任务 (test_tasks.json)

```json
{
  "meta": { "generatedAt": "...", "pipeline": "plan_tree->static->interface->logic->quality" },
  "testTasks": [
    {
      "id": "t_auth_001",
      "layer": "auth",
      "testType": "interface",
      "sourceTask": "t_backend_auth_01",
      "targetFiles": ["middleware/auth.js"],
      "dependencies": ["t_infra_01"],
      "testFramework": "jest",
      "checkPoints": ["导出 authenticate", "导出 optionalAuth", "Token 过期 → 401"],
      "testScenarios": [
        {"category": "correct", "scenario": "有效 token → 200", "expectedBehavior": "返回用户信息"},
        {"category": "error", "scenario": "过期 token → 401", "expectedBehavior": "返回认证失败"},
        {"category": "boundary", "scenario": "无 token → 401", "expectedBehavior": "返回未认证"}
      ]
    }
  ]
}
```

### 9.3 测试状态 (test_logs)

```json
{
  "task_id": "t_auth_001",
  "test_success": true,
  "source_success": true,
  "test_file_path": "test/t_auth_001.test.js",
  "attempt": 3,
  "done": true,
  "best_score": 0.95,
  "best_attempt": 2,
  "state": "(TS, SS)"
}
```

---

## 第十章：错误处理与容错

### 10.1 多层容错策略

```
┌────────────────────────────────────────────────────────────┐
│  Layer 1: API 错误重试                                      │
│  - base_designer: API 错误自动重试 1 次 (新 Agent 实例)     │
│  - model_client: httpx 超时 + 1 次重试                      │
│  - Monkey-patch: DeepSeek 兼容性修复 (null description)     │
│                                                            │
│  Layer 2: Agent 输出解析回退                                 │
│  - 策略 1: <!--FINAL--> 双标记 JSON (最可靠)                │
│  - 策略 2: 单标记 + 括号深度追踪                             │
│  - 策略 3: 双标记之间全文搜索 JSON                            │
│  - 策略 4: 文本格式 ban (f=...|b=...)                       │
│  - 策略 5: 回退结果 (测试结果数字 → 构造默认 ban)            │
│                                                            │
│  Layer 3: 调度器容错                                        │
│  - 任务失败 → 标记 failed → 剪枝下游                         │
│  - 状态持久化 → 恢复模式跳过已完成任务                        │
│  - 多轮 ABCD → 无进展检测 (passed <= prev_passed → 停止)     │
│                                                            │
│  Layer 4: 确定性修复                                        │
│  - 路由自动注入 (app.js 缺路由 → Python 扫描 routes/ → 注入)  │
│  - 多路由展开 (module.exports = {a,b} → 分别 app.use)       │
│  - 死路由清理 (router/index.js 不存在 .vue → 注释)          │
│  - env 补全 (代码 scan → 缺失变量 → .env 追加)               │
└────────────────────────────────────────────────────────────┘
```

### 10.2 JSON 提取多层回退

```python
# agent/source_fixer.py — _extract_structured()
def _extract_structured(text: str) -> tuple:
    """4 层回退策略:"""

    # 策略 1: <!--FINAL-->[...]<!--FINAL--> 或 {...} 双标记
    for m in re.finditer(r'<!--FINAL-->\s*(\[.*?\]|\{.*?\})\s*<!--FINAL-->', tail):
        data = try_parse(m.group(1))
        if valid(data): return (None, data) if list else (data, None)

    # 策略 2: 单标记 + 括号深度追踪 (处理 LLM 忘记闭合标记)
    for m2 in re.finditer(r'<!--FINAL-->\s*([\[\{])', tail):
        # 从起始括号追踪到匹配的闭合括号

    # 策略 3: 双标记之间全文搜索 JSON
    for m3 in re.finditer(r'<!--FINAL-->(.*?)<!--FINAL-->', tail):
        # 在 inner 中搜索所有 JSON 块，取最后一个有效项

    # 策略 4: 文本格式 fallback
    for fm in re.finditer(r'[fF]\s*=\s*(.+?)\s*\|\s*[bB]\s*=\s*(.+?)(?:\n|$)', tail):
        bans.append({"f": f_val, "b": b_val})
```

---

## 第十一章：系统配置

### 11.1 环境变量体系

```bash
# .env.example — 完整配置

# ── LLM 配置 ──
OPENAI_API_KEY="sk-xxx"                    # DeepSeek API Key
OPENAI_BASE_URL="https://api.deepseek.com"  # API 地址
OPENAI_MODEL="deepseek-v4-pro"             # 模型
DEEPSEEK_BALANCE_URL="https://api.deepseek.com/user/balance"

# ── 本地 LLM (可选) ──
LOCAL_OPENAI_API_KEY="111"                # 本地不需要真实密钥
LOCAL_OPENAI_BASE_URL="http://localhost:3002/completion"
LOCAL_OPENAI_V1_URL="http://localhost:3002/v1"
LOCAL_OPENAI_MODEL="Qwopus3.5-4B-coder-Q4_K_M.gguf"
LOCAL_CTX_SIZE=32768
LOCAL_TIMEOUT=600
LOCAL_MAX_TOKENS=4096

# ── HTTP 超时 ──
HTTP_CONNECT_TIMEOUT=10
HTTP_READ_TIMEOUT=120
HTTP_WRITE_TIMEOUT=30
HTTP_POOL_TIMEOUT=10
HTTP_MAX_RETRIES=1

# ── RAG ──
RAG_EMBEDDING_MODEL="Qwen/Qwen3-Embedding-4B"
RAG_RERANKER_MODEL="Qwen/Qwen3-Reranker-4B"
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=80
RAG_TABLE="knowledge"
RAG_BUILD_TABLE="knowledge_base"

# ── 数据库 ──
DB_HOST="localhost"
DB_PORT="3306"
DB_USER="root"
DB_PASSWORD="xxx"
DB_NAME="testdb"

# ── 缓存 ──
REDIS_URL="redis://localhost:6379/0"
RAG_CACHE_TTL=86400

# ── 服务 ──
PORT="3000"
```

### 11.2 Python 依赖

```
picoagents          # Agent 框架 (含 LLM 客户端 + 流式处理 + 工具系统)
python-dotenv       # .env 加载
lancedb             # 向量数据库 (RAG)
pyarrow             # Arrow 数据格式 (LanceDB 依赖)
sentence-transformers # Embedding 模型
numpy               # 数值计算
redis               # 缓存 (可选)
```

---

## 第十二章：系统性能特征

| 指标 | 值 | 说明 |
|------|------|------|
| Agent 最大迭代次数 | 3-7 | 按任务复杂度动态设定 |
| 最大并发任务数 | 100 | asyncio.gather 自然上限 |
| 单次 LLM 调用最大 ctx | ~128K | DeepSeek 模型上下文窗口 |
| System Prompt 缓存命中率 | >60% | 共享 skill 固定在前 |
| 语法检查超时 | 15s | node --check / esbuild |
| Vite 构建超时 | 120s | 前端的完整构建 |
| npm install 超时 | 600s | 首次安装可能较慢 |
| 全量测试超时 | 300s | jest --json --forceExit |
| MySQL 连接超时 | 5s | db_api 层服务检查 |
| Token 追踪开销 | 0 | 纯旁路观测，无额外 LLM 调用 |

---

## 附录 A：文件命名规范

| 路径模式 | 说明 |
|---------|------|
| `Memory/agent_logs/{category}/{run_id}/{idx}_{step}.md` | Agent 对话实录 |
| `Memory/agent_logs/{category}/{task_id}/{step}_{name}.md` | 步骤日志 |
| `Memory/truths/engineer/{taskId}.json` | 工程师真理文件 |
| `Memory/test_failure/{taskId}.json` | 测试失败 ban |
| `Memory/source_failure/{taskId}.json` | 源码失败 ban |
| `Memory/test_logs/{taskId}.json` | 测试状态 |
| `Memory/architect/_contracts_{layer}.json` | 架构师中间契约 |
| `Memory/test_architect/_test_{layer}.json` | 测试架构师中间产物 |
| `work/project/doc/requirement_report_{session}_{ts}.md` | PRD 报告 |
| `work/project/task/task_{ts}.json` | 架构任务文件 |
| `work/project/task/_scene_tree.md` | 场景树 |
| `work/project/test/test_tasks_{ts}.json` | 测试任务文件 |
| `work/project/test/{taskId}.test.js` | 测试代码 |
| `token/{category}/{ts}_{taskId}.json` | Token 报告 |

## 附录 B：关键类型映射

```
engineer type → test layer 映射 (_LAYER_TO_TYPE):
  infra/repair    → static
  db              → static
  frontend        → static
  peer_deps       → static
  integ           → static
  auth            → interface
  db_api          → interface
  api             → interface
  navigation      → interface
  backend_proc    → logic
  logic           → logic
  scenario        → logic
  nfr             → quality

engineer type 执行优先级:
  infra (0) > db (1) > frontend (2) > backend (3) > integration (4)

test type 执行优先级:
  static (0) > interface (1) > logic (2) > quality (3)
```

# Agent — 多智能体代码生成系统

> 一句话需求 → 完整 Web 应用源码（Node.js + Express + MySQL + Vue 3），全自动生成。

## 这是什么

输入一句自然语言需求描述，系统通过五个阶段的智能体协作自动产出可运行的项目，包括 PRD 文档、架构契约、前后端源码、数据库 DDL、测试代码，以及自动化测试修复闭环。

```
一句话需求
  → 需求分析 (PM + 10角色多轮讨论 → PRD)
  → 架构设计 (7类契约 + 5类工程任务)
  → 代码生成 (infra→db→frontend→backend→integration 分层并发)
  → 测试架构 (4层173个测试任务)
  → ABCD 测试修复闭环 (写测试→诊断→修复→验证，多轮收敛)
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 3. 运行
python brainAgent/basic.py "设计一个电商平台"
```

**分阶段运行**：

```bash
python brainAgent/basic.py -orchestrator "需求"   # 只做需求分析
python brainAgent/basic.py -architect             # 从架构设计开始
python brainAgent/basic.py -engineer              # 从代码生成开始
python brainAgent/basic.py -engineer --resume     # 恢复模式
python brainAgent/basic.py -test                  # 只跑测试执行
```

## 工作原理

### 五阶段流水线

| 阶段 | Agent | 产物 |
|------|------|------|
| **需求分析** | PM Planner + 10 角色子Agent（customer/user/manager/innovator/business/qa/data/architect/security/designer）多轮讨论 | PRD 报告 + UI 设计令牌 |
| **架构设计** | Architect — 5 步流水线（plan_tree→data→interfaces→business→tasks） | 7 类契约（model/auth/api/db-api/navigation/scenario/logic）+ 5 类工程任务 |
| **代码生成** | 5 类工程师（infra/db/frontend/backend/integration）DAG 分层并发 | 完整项目源码 + 真理文件 |
| **测试架构** | TestArchitect — 分层流水线（static→interface→logic→quality） | 173 个分层测试任务 |
| **测试修复** | ABCD 闭环：A(test_writer)→B(test_runner)→C(source_fixer)→D(verify) | 通过测试的源码 + Ban 经验记忆 |

### 生成的产物技术栈

| 层 | 技术 |
|------|------|
| 后端 | Node.js + Express + mysql2 |
| 数据库 | MySQL（DDL + 种子数据） |
| 认证 | JWT（jsonwebtoken + bcrypt） |
| 前端 | Vue 3 + Vite + Pinia + Element Plus |
| 测试 | Jest + supertest + k6 |

## 目录结构

```
Agent/
├── agent/                  # 核心 Agent 实现
│   ├── product_manager.py   # PM + 10 角色子Agent
│   ├── architect.py         # 架构师 — 契约生成流水线
│   ├── base_designer.py     # 工程师基类（infra/db/backend/frontend）
│   ├── integrator.py        # 集成工程师
│   ├── prompt_builder.py    # 统一提示词组装
│   ├── test_architect.py    # 测试架构师
│   ├── test_writer.py       # A 步骤：测试编写
│   ├── test_runner.py       # B/D 步骤：测试诊断/验证
│   └── source_fixer.py      # C 步骤：源码修复
│
├── brainAgent/              # 编排调度层
│   ├── basic.py             # CLI 统一入口
│   ├── orchestrator.py      # 需求分析编排
│   ├── engineer.py          # 代码生成调度
│   ├── scheduler.py         # ABCD 测试调度
│   ├── knowledge_builder.py # RAG 知识库构建
│   └── retrieval_scheduler.py # RAG 检索调度
│
├── skill/                   # Agent 技能文档（121 文件）
│   ├── design/              # 需求分析角色技能
│   ├── engineer/            # 架构 + 代码生成技能
│   ├── test/                # 测试全链路技能
│   ├── code/                # 代码质量规范
│   └── rag/                 # RAG 构建/检索技能
│
├── Tools/                   # 可复用工具
│   ├── coding/              # 文件创建/读取/编辑/语法检查
│   ├── testing/             # 测试运行 + npm 安装
│   ├── memory/              # 记忆/Ban 管理
│   ├── rag/                 # RAG 检索 + 知识库构建
│   ├── contract/            # 契约解析
│   └── scoring/             # 代码评分
│
├── utils/                   # 共享基础设施
│   ├── model_client.py       # LLM 客户端
│   ├── token_tracker.py      # Token 消耗追踪
│   ├── token.py              # Token 流处理
│   └── dependency_graph.py   # DAG 分层算法
│
├── localAgent/              # RAG 专用 LLM Agent
│   ├── knowledge_builder.py  # 经验净化 + 语义合并
│   └── retrieval_agent.py    # 角度分析 + 结果交付
│
├── doc/                     # 文档
│   ├── README.md             # 用户文档
│   └── SYSTEM_ARCHITECTURE.md # 系统架构设计
│
└── requirements.txt         # Python 依赖
```

## 配置

主要环境变量（`.env.example`）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | LLM API Key | — |
| `OPENAI_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `OPENAI_MODEL` | 模型 | `deepseek-v4-pro` |
| `DB_HOST/PORT/USER/PASSWORD/NAME` | MySQL | localhost:3306 |
| `REDIS_URL` | Redis 缓存 | `redis://localhost:6379/0` |
| `RAG_EMBEDDING_MODEL` | 向量嵌入模型 | `Qwen/Qwen3-Embedding-4B` |

## 环境要求

- Python 3.11+
- DeepSeek API Key（或其他 OpenAI 兼容 API）
- Node.js（生成产物运行时需要）
- MySQL（生成产物运行时需要，测试阶段必需）
- Redis（可选，用于缓存）

## 文档

- [用户文档](doc/README.md) — 详细的功能介绍和使用指南
- [系统架构设计](doc/SYSTEM_ARCHITECTURE.md) — 完整的架构设计文档

## License

MIT

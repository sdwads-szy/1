# Agent 多智能体代码生成系统

> 从一句话需求 → 完整 Web 应用（Node.js + Express + MySQL + Vue 3），全自动生成。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY（DeepSeek API Key）

# 3. 运行
python brainAgent/basic.py "设计一个电商平台"
```

## 能力范围（当前版本）

```
✅ Step 1  需求分析     PM Agent 多角色讨论 → PRD 报告
✅ Step 2  架构设计     Architect Agent → 7类契约 + 5类任务
✅ Step 3  代码生成     5类工程师分层并发 + 集成 → 完整源码
✅ Step 4a 测试架构     TestArchitect Agent → 测试任务清单
🚧 Step 4b ABCD 循环   测试运行 + 自动修复（加强中）
```

> **当前版本**：需求 → 架构 → 代码 → 测试任务清单。

## 路线图

```
Step 4b ABCD 循环（开发中）
  A 写测试 → B 运行诊断 → C 修复源码 → D 验证修复
  └─ 多轮迭代，逐层收敛
     ├─ 对齐 PRD：确保功能实现与需求一致
     ├─ 对齐 Task：确保接口签名与契约一致
     └─ 收敛终点：全部 test_tasks 通过，测试覆盖率达标
```

## 当前产物

本次运行生成了一个**多商户电商平台**：

| 类型 | 数量 | 说明 |
|------|------|------|
| 后端路由 | 12 | Express 路由 + 中间件 + 数据库 |
| 前端页面 | 41 | Vue 3 页面（前台 + 商家 + 管理后台） |
| SQL 表 | 12 | 用户/商品/订单/优惠券/退款/搜索... |
| 测试计划 | 1 | 168KB 测试任务清单 |

## 目录结构

```
Agent/
├── agent/              # 核心 Agent 实现 (13 文件)
├── brainAgent/         # 编排调度器 (7 文件)
├── config/             # 配置文件 (4 文件)
├── skill/              # Agent 技能文档 (103 文件)
├── Tools/              # 可复用工具 (20+ 文件)
├── localAgent/         # LLM 调用封装
├── utils/              # 共享工具
├── work/project/       # 生成产物 ← 本次运行输出
│   ├── routes/         #   后端 API 路由
│   ├── services/       #   业务逻辑层
│   ├── middleware/     #   认证/权限/错误处理
│   ├── database/       #   DDL 脚本
│   ├── src/pages/      #   Vue 3 页面
│   ├── src/stores/     #   Pinia 状态管理
│   ├── src/router/     #   前端路由
│   └── test/           #   测试任务清单
└── requirements.txt    # Python 依赖
```

## CLI 用法

```bash
# 全流程
python brainAgent/basic.py "需求"

# 分阶段
python brainAgent/basic.py -orchestrator "需求"   # 只要需求分析
python brainAgent/basic.py -architect             # 从架构设计开始
python brainAgent/basic.py -engineer --resume     # 恢复代码生成
python brainAgent/basic.py -test                  # 从测试开始
```

## 本次运行状态

| 阶段 | 状态 | 产物 |
|------|------|------|
| Step 1 需求分析 | ✅ | `requirement_report_*.md` (22KB) |
| Step 2 架构设计 | ✅ | `task_*.json` (217KB, 7类契约+5类任务) |
| Step 3 代码生成 | ✅ | 76 JS + 41 Vue + 12 SQL |
| Step 3 集成 | ✅ | 12 routes + 41 pages 路径对齐 |
| Step 4a 测试架构 | ✅ | `test_tasks_*.json` (168KB, 13层测试计划) |
| Step 4b ABCD 循环 | 🚧 | 对齐 PRD + Task → 收敛于 test_tasks |

## 依赖

- Python 3.11+
- DeepSeek API Key（或其他 OpenAI 兼容 API）
- Node.js（仅生成的产物需要）
- MySQL / Redis（可选）

## License

MIT

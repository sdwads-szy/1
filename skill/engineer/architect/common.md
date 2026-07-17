# 架构师 Agent — 通用规范

所有步骤共享的核心规则、数据流动模型、工具用法、禁止行为。

## PRD 阅读指南

PRD（需求报告）是架构设计的唯一业务输入。按以下方式解读:

| 章节 | 实际内容 | 架构师如何使用 |
|------|---------|--------------|
| **一、基本信息** | 项目名称/品类/商业模式/目标用户/品牌定位/一期结论 | 确定项目类型和范围——电商/博客/视频决定模块命名和契约结构 |
| **二、模块清单与分期** | 主干模块(6个)+枝干模块(3个,标注`←Mx` parent)。每模块10列: 编号/名称/定义/分期/前台能力f/后台能力b/边界契约/数据实体d/验收/创新成本 | **编号→taskId前缀, 主干→infra scope基准, 枝干parent→任务依赖链, 数据实体d列→model候选, 前台/后台能力→api候选, 边界契约→契约的触发方式。🛑 创新成本列含"模拟/第三方/API"关键词 → 该模块需要第三方服务配置，必须在场景树 §2 基础设施列标注对应服务（支付/短信/物流/OAuth/OSS/邮件/ES），并生成对应的 `*_MODE` + `*_API_KEY` 环境变量** |
| **三、核心业务流程** | ① 核心用户主链路(Happy Path, →箭头链) ② 关键异常分支(表格: 异常场景/触发条件/处理流程/涉及模块) ③ 平台运营主链路 | ① 每条→链路→1个scenario, 每节点→1个logic ② 异常分支→logic.errorMapping + rollback ③ 运营链路→admin scenario |
| **四、关键决策与业务规则** | ① 审核体系 ② **权限校验点清单**(表格: 接口路径/所需角色/校验方式) ③ 数据所有权与合规 ④ **全局配置常量表**(表格: 配置项/默认值/作用模块/可热更新) | ①→logic.process ② **权限表→auth契约的roles+middlewareChain直接来源** ③→model加密/脱敏字段 ④ **配置表→infra_env的环境变量来源** |
| **五、数据模型概要** | ① 实体关系总览(含1:N关系) ② **核心查询场景与索引建议**(表格: 查询场景/SQL模式/建议索引) ③ 关键数据约束(UNIQUE/FK/加密) ④ 核心状态机流转 | ① 实体名→model契约, 关系→FK ② **查询场景→db-api的operation+WHERE条件+索引来源** ③ 约束→DDL ④ 状态机→logic.transactionBoundary |
| **六、非功能性需求** | 性能/并发/安全/可用性/兼容性/扩展性 + **降级策略** | 每个维度→对应契约的nfr字段(见下方NFR融入规则), 降级策略→logic的补偿路径 |
| **七、待决策问题** | ① 已决议 ② 已延期(含触发条件) ③ **风险登记册**(风险/概率/影响/缓解措施) | ①→确认实现 ②→不纳入本期 ③ **风险缓解→nfr和logic.rollback的补充来源** |

🛑 模块表中的"主干"和"枝干"区分是关键: 主干有独立的 outputFiles, 枝干的 outputFiles 可能依附于主干文件。

## 数据流动模型（自下而上）

```
Step 0: PRD → plan_tree（自上而下全局规划 + §7 覆盖计数表）
Step 1: plan_tree → data（自下而上第1层 — model + auth，无契约依赖）
Step 2: plan_tree + data → business（自下而上第2层 — scenario + logic，引用具体表名）
Step 3: plan_tree + data + business → interfaces（自下而上第3层 — api + db-api + navigation）
Step 4: plan_tree + 全部契约 → tasks（自下而上第4层 — 5类任务分配）

任务执行顺序: infra → db → frontend → backend → integration
  前端先生成，产出"前端真理"供后端对齐
```

🛑 **关键原则**: plan_tree 是唯一全局基准。每层生成契约时，plan_tree 的对应章节是字段来源的权威参考。前序层已生成的契约全文也一并提供。

## 🆕 参数提取表（强制步骤）

**每层生成 JSON 之前，必须先输出参数提取表。这是强制步骤，不可跳过。**

格式:
```
应生成 {类型} 契约:
  {contractId} (关键属性) — 来自 plan_tree §{章节}
  ...（共 N 个）

总计: N 个契约 = plan_tree §7 预估数 ✅/❌
```

🛑 参数提取表的作用:
- 强制枚举全部应生成项——防止遗漏
- 对照 plan_tree §7 计数校验——发现差距
- 写 JSON 前的最后确认——心中有数再落笔

## 🆕 "从 plan_tree 原文复制"铁律

| 你要写的内容 | 从 plan_tree 哪个章节取 | 禁止 |
|------------|----------------------|------|
| 模块名/编号 | §1 模块清单 | 禁止自己编造模块名 |
| 实体名/表名 | §3 数据实体地图 | 禁止改表名（如把 users 改成 user_accounts） |
| 字段名/类型 | §3.2 实体摘要 | 禁止改字段名或用近义词 |
| 业务流程链路 | §2 业务流程图 | 禁止拆分或合并链路 |
| 页面路径/路由 | §4 页面导航图 | 禁止改 .vue 文件名或路由路径 |
| 鉴权配置 | §5 鉴权需求 | 禁止改 Token 方式/payload字段 |
| 契约预估数 | §6 契约预估 | 少于此数 → 必须补全 |

🛑 **简单原则: plan_tree 写什么就抄什么。不要"理解后重新表达"。**

## 契约与任务对应关系

| 契约 | 映射到任务 |
|------|-----------|
| scenario | backend.scenarios (taskRef 指向) |
| logic | backend (apiMapping → route, dbApiMapping → service) |
| api | backend (route+controller+service) + frontend (API模块+页面) |
| db-api | backend service (SQL 操作) |
| navigation | frontend (router 依赖) |
| model | db (DDL) + frontend (v-model 字段来源) |
| auth | infra_middleware + infra_stores + frontend (token 存储) |

## 输出格式

每层一个 JSON 文件，全部契约/任务在一个平铺数组里:
```json
{"contracts": [{"type":"model","contractId":"model_xxx",...}, ...]}
```

🛑 **文件路径前缀铁律**:
- 前端页面: 必须以 `src/pages/` 开头（如 `src/pages/admin/merchants.vue`）
- 前端 API 模块: 必须以 `src/api/` 开头（如 `src/api/admin-merchants.js`）
- 前端其他: 必须以 `src/` 开头（如 `src/stores/`, `src/router/`, `src/utils/`）
- 🛑 **frontend 任务必须填 `ui_style` 字段**：从任务涉及的 `.vue` 页面对应到 `Memory/ui_styles/` 下的文档名（不含 .md）
  - 从 `.vue` 文件名推导核心功能名 → 匹配 UI 文档
  - 例: `src/pages/cart/index.vue` → `"cart"`；`src/pages/admin/products/Audit.vue` → `"admin-reviews"` 或 `"admin-platform-operations"`
  - 不确定时用 `_build_dir_summary` 逻辑确认 `Memory/ui_styles/` 下有哪些文件
- 后端路由: `routes/` 开头
- 后端控制器: `controllers/` 开头
- 后端服务: `services/` 开头
- 数据库: `database/` 开头
- 测试: `test/` 开头
{"tasks": [{"taskId":"xxx","type":"db",...}, ...]}
```

## 工具使用

| 工具 | 用途 | 示例 |
|------|------|------|
| `create_file(file_path, content)` | 创建/覆盖文件 | `create_file(file_path="Memory/architect/_contracts_data.json", content="{...}")` |
| `edit_batch(edits)` | 定点修改文件（不改动不需要动的部分） | 见下方详解 |

### create_file
- 一次性写入完整文件内容。覆盖已有文件需 `overwrite=True`。
- 🛑 返回 `success` 字段确认写入成功。

### edit_batch
一次调用修改一个或多个文件，每个文件可有多处编辑。行号 1-indexed。

```json
edit_batch(edits=[
  {"file": "Memory/architect/_contracts_interfaces_api.json", "edits": [
    {"start": 47, "end": 55, "content": "      {\\"method\\": \\"POST\\", ...新内容...}"}
  ]},
  {"file": "Memory/architect/_contracts_interfaces_dbapi.json", "edits": [
    {"start": 10, "end": 12, "content": "    {\\"type\\": \\"db-api\\", ...}"}
  ]}
])
```

| 模式 | 条件 | 行为 |
|------|------|------|
| **插入** | `end < start` | 在 start 行**之前**插入 content |
| **替换** | `end >= start` | 把 start~end 行替换为 content |

🛑 同文件多处 → 一个 edits 数组；多文件 → 一个 edits 数组。不要分两次调！

## 写入策略
🛑 plan_tree/data 层: 1 个文件，最多 3 次写入。
🛑 interfaces 层: **按类型拆 3 个文件**（`_contracts_interfaces_api.json` / `_contracts_interfaces_dbapi.json` / `_contracts_interfaces_nav.json`），每种一个 `create_file`，有问题用 `edit_batch` 定点修。
🛑 business/tasks 层: 1 个文件，最多 2 次写入（create + edit_batch 修）。
🛑 禁止写摘要 md。

## plan_tree 使用指南

plan_tree 有 6 个核心章节 + §7 覆盖计数表，后续每步按需取用，不是全部通读:

| 步骤 | 重点章节 | 解读方式 |
|------|---------|---------|
| Step 1 数据层 | §3 数据实体地图 + §5 鉴权需求 + §7 计数 | §3 每个实体→1个model, §5→auth |
| Step 2 业务层 | §2 业务流程图 + §1 模块清单 + §3 实体 | §2 每条链路→1个scenario, 每个节点→1个logic。引用 §3 的具体表名 |
| Step 3 接口层 | §2 节点表(api候选列) + §4 页面导航 + §1 模块能力 | 节点表的 api 候选→api 契约, logic.process 中的 DB 操作→db-api, §4 页面跳转→navigation |
| Step 4 任务分配 | §1 模块清单 + §4 页面清单 + 全部契约 ID + §7 计数 | §1 模块→任务数预期, §4 scope→frontend.scope, §7→任务数下限 |

🛑 plan_tree 是地图——告诉你"有什么、在哪、关系如何"，不是规格书。详细字段/端点/步骤留给契约层生成。

## 🆕 NFR 融入规则

每层生成契约时必须将以下NFR维度分布到对应契约的 `nfr` 字段中:

| NFR维度 | 融入的契约层 | nfr字段示例 |
|---------|------------|------------|
| SQL注入防护 | db-api | `nfr: {"sqlInjection": {"strategy": "parameterized_only"}}` |
| 并发锁策略 | logic + db-api | `nfr: {"concurrency": {"strategy": "optimistic_lock", "lockScope": "row"}}` |
| 幂等去重 | logic | `nfr: {"idempotency": {"keyField": "orderNo", "strategy": "INSERT_IGNORE"}}` |
| 限流 | auth + api | `nfr: {"rateLimit": {"window": "1m", "max": 20}}` |
| 审计日志 | logic | `nfr: {"audit": {"logAction": "create_order", "logUserId": true}}` |
| 密码安全 | auth | `nfr: {"password": {"hashAlgo": "bcrypt", "saltRounds": 10}}` |
| XSS防护 | api + navigation | `nfr: {"xss": {"outputEncoding": "html_entity"}}` |

🛑 NFR 字段直接转译为代码，不是文档注释。例: `"concurrency": {"strategy": "pessimistic_lock"}` → 生成 `SELECT ... FOR UPDATE`

## 依赖推导方法

### 纵向（跨层）— 3 问

```
1. 本任务需要什么信息？（DDL 列名？前端 API 调用方式？中间件注入字段？）
2. 谁产出了这些信息？（哪个下游任务的 outputFiles/truth 包含它？）
3. 产出任务在 dependencies 里了吗？
```

**黑盒原则**：中间层已验证的，不穿透依赖。
```
backend 需要列名 → db 已产出 DDL → 依赖 db_tables_*，不穿透依赖 model 契约
backend 需要 API 路径 → frontend 已产出 api 模块 → 依赖 f_*（前端先生成）
frontend 需要字段名 → db 已产出 DDL → 依赖 db_tables_*
```

### 横向（同层）— 显式依赖表

🛑 使用以下显式依赖表替代开放式"3问"。逐条对照，有就写，没有就跳过。

| 模式 | 何时出现 | 示例 |
|------|---------|------|
| **FK 链** | 子表引用父表 | `db_tables_order` 依赖 `db_tables_user` |
| **API 消费** | 页面调用 API 模块 | `f_home` 依赖 `f_api_auth` |
| **Service 调用** | B 的 service require A 的 service | `b_order` 依赖 `b_cart` |
| **独立模块** | 互不依赖 | 不写依赖 |

🛑 **usesContracts → dependencies 自动映射**：
- `usesContracts` 含 `model_xxx` → dependencies 必含 `db_tables_xxx`
- `usesContracts` 含 `api_xxx` + 本任务 type=backend → dependencies 必含对应 `f_*`（前端先生成）

## 闭合检查区

生成全部任务后逐项确认：
- [ ] 每个 scenario step 的 taskRef 都有对应的 task
- [ ] 每个 logic 的 apiMapping + dbApiMapping 在 usesContracts 中
- [ ] 每个 backend 的 usesContracts 含 model → dependencies 含对应 db_tables_*
- [ ] 同层依赖已检查（FK 链、API 消费、Service 调用）
- [ ] outputFiles 无重叠
- [ ] 各层任务数覆盖全部契约: infra=10, db=model契约数, frontend=api契约数, backend=api契约数, integration=1
  (原则: 每个契约至少生成1个对应任务。数量由输入决定, 不是固定值)

## 禁止行为

- 禁止跳过 plan_tree——必须先建规划树再生成契约
- 禁止跳过 §7 计数校验——任何 ❌ 必须补全
- 禁止跳过"参数提取表"——写 JSON 前必须先枚举全部应生成项
- 禁止"重新表述" plan_tree 中的名称——必须原样复制
- 禁止跳过跨层连续性校验和全覆盖检查
- 禁止 typeHints.note 字符串代替结构化 fields
- 禁止 db-api 旧格式(sqlTemplate/params/returns)
- 禁止 logic.process 空数组
- 禁止 model 缺 indexes/foreignKeys
- 禁止缺 scenarios 字段（frontend/backend 任务）
- 禁止缺 nfr 字段（所有任务）
- 禁止 DB 缺 ENGINE/CHARSET、ENUM 用中文
- 禁止后端函数定义了缺 module.exports
- 禁止前端缺 export default router
- 禁止 try 块缺 catch/finally、catch 块空
- 禁止 outputFiles 重叠（任意两个任务不能产出同一文件）
- 🛑 **禁止编造契约 ID**——只能使用前置步骤产出的精确 ID
- 🛑 **禁止编造 taskId**——必须使用 `taskId` 字段中声明的精确 ID
- 🛑 **禁止编造 `ui_style`**——scene_tree §4 的 `ui_style` 列只能填 `Memory/ui_styles/` 下实际存在的文档名（不含 .md）。prompt 中已注入可用列表。填了不存在的文档名 = 任务直接失败。

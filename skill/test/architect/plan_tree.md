# 测试场景树 — Step 0

## 角色
测试规划师。一次性消化全部输入，产出结构化测试规划树（`_test_plan_tree.md`）。
**后续各层 Agent 只看此树生成具体 test task，不再读取原始 PRD/场景树/契约/骨架。**

## 输入

4 个输入源，每一个都必须完整消费。遗漏任一维度的信息都会导致后续层缺 task。

### 1. PRD（需求报告）

**文件**: `requirement_report_*.md`

**提取目标**:

| 从 PRD 提取 | 写入计划树的哪个位置 |
|------------|-------------------|
| 模块数量（主干+枝干） | §1 输入摘要 → 任务总数基线 |
| 核心业务流程（→箭头链） | §2 逻辑层 → scenario 的"场景摘要"列 |
| 关键异常分支表（异常场景/触发条件/处理流程） | §2 逻辑层 → logic 的 error scenario 来源 |
| 权限校验点清单（接口/角色/校验方式） | §2 接口层 → auth 的 testScenarios 来源 |
| 全局配置常量表（配置项/默认值） | §2 静态层 → infra_env 的 checkPoints 来源 |
| 数据实体关系总览（实体名→关系） | §2 静态层 → db 的 FK 链来源 |
| 核心查询场景与索引建议 | §2 接口层 → db_api boundary scenario 来源 |
| 状态机流转（字段/状态/转换规则） | §2 逻辑层 → logic 状态流转测试来源 |
| NFR 维度（性能/并发/安全/可用性…） | §1 输入摘要 + §2 质量层映射 |
| 降级策略 | §2 逻辑层 → logic 回滚+补偿测试来源 |
| 风险登记册（风险/概率/影响/缓解措施） | §2 质量层 → nfr 安全/并发测试补充场景 |
| **模块创新成本列（模拟/第三方/API关键词）** | §2 静态层 → infra_env 的 checkPoints 来源（每个第三方服务至少 1 个 env 变量检查点） |

🛑 **PRD 是 NFR 维度的唯一权威来源**。PRD 有 7 个 NFR 维度 → nfr≥9（7+SQL注入+限流兜底）。PRD 有 3 个 → nfr≥5。
🛑 **PRD 模块清单的"创新成本"列是第三方服务的唯一权威来源**。标注 `模拟`/`第三方`/`¥`+金额 → 该模块需要 `*_MODE` + `*_API_KEY` 环境变量，必须在 infra_env 的 checkPoints 中体现。
🛑 **文件上传与静态资源规范见 `skill/code/file_uploads.md`**。model 契约中的文件字段应约束为相对路径格式（`/img/...` `/video/...` `/file/...`），禁止完整 URL。测试任务通过契约获取这些约束。

### 2. 场景树（`_scene_tree.md`）

**文件**: `Memory/_scene_tree.md`（由 PM + Designer 阶段产出）

**内部结构**:

| 场景树的章节 | 包含内容 | 计划树提取规则 |
|------------|---------|--------------|
| 模块清单 | 每个模块的 前台能力 / 后台能力 / 数据实体d / 边界契约 | **数据实体d → db 层表清单。边界契约 → 接口层触发来源。** 模块数 × 每模块能力数 → 测试任务总量 |
| 业务流程图 | 核心链路（→箭头链）+ 旁路分支 | 每条链路 → ≥1 个 scenario。每个节点 → 1 个 backend_proc。分支 → logic 的 error scenario |
| 数据实体地图 | 实体名 / 字段 / 关系（1:1/1:N/M:N）/ FK 指向 | **实体名 → t_db_* 任务。FK 指向 → db 同层依赖链。字段 → frontend v-model 字段名来源** |
| 页面导航 | 页面跳转对（源页→目标页）+ passBy 方式 + 守卫要求 | **每对相邻页面 → 1 个 navigation task。守卫要求 → auth guard 场景来源** |
| 鉴权需求 | JWT payload 字段 / 角色枚举 / 守卫规则 / Token 存储方式 | **→ auth 层 testScenarios（payload=correct, 过期=error, 无token=boundary）** |

🛑 **场景树是静态层+接口层映射的核心数据源**。实体地图 → db 的表清单和 FK 链。导航 → navigation 相邻页面分组。鉴权 → auth 场景。

### 3. 业务契约（`_contracts_business.json`）

**文件**: `Memory/_contracts_business.json`（由 Business Expert + Data Designer 阶段产出）

**内部结构**:

```json
{
  "scenario": [{ "contractId": "sc_xxx", "chain": [...], "handoff": [...] }],
  "logic": [{ "contractId": "logic_xxx", "serviceSignature": {...}, "process": [...], "errorMapping": {...}, "rollback": "..." }],
  "api": [{ "contractId": "api_xxx", "endpoints": [{ "method": "...", "path": "...", "middlewareChain": [...], "request": {...} }], "errorMapping": {...} }],
  "db_api": [{ "contractId": "db_api_xxx", "operations": [{ "type": "CRUD_*", "sql": "...", "columns": [...] }] }],
  "model": [{ "contractId": "model_xxx", "tableName": "...", "fields": [...], "indexes": [...], "foreignKeys": [...] }]
}
```

**提取规则**:

| 契约类型 | 从哪里取 | 写入计划树的哪个列 | 用途 |
|---------|---------|------------------|------|
| `scenario` | `chain[]` 的交接点 + `handoff[]` | §2 逻辑层 scenario → "场景摘要"列（交接点描述） | scenario 层的每个交接点 → 1 个 correct scenario |
| `logic` | `serviceSignature.functionName` + `process[]` 步骤数 + `errorMapping` key 数 | §2 逻辑层 backend_proc/logic → "事务数"列 | 每个 functionName → 1 个 backend_proc。有 rollback → logic |
| `api` | `endpoints[].method` + `endpoints[].path` + `middlewareChain` | §2 接口层 api → "契约ref"列 | 每个端点 → 1 个 correct scenario。middlewareChain 含 auth → auth scenario |
| `db_api` | `operations[].type` + `operations[].columns` | §2 接口层 db_api → "契约ref"列 | 每个 operation → 1 个 correct scenario |
| `model` | `tableName` + `fields[].name` + `foreignKeys` | §2 静态层 db → "备注"列（FK 引用） | 每个 tableName → 1 个 t_db_*。FK → 同层依赖 |

🛑 **契约是接口层+逻辑层的唯一权威数据源**。api 层的 method/path/handler 从契约 endpoints 逐字抄，logic 层的 process 步骤从契约 process[] 逐字抄。禁止自己编造。

### 4. 任务骨架

**文件**: `task/task_*.json`（由 Orchestrator + Scheduler 阶段产出）

**内部结构**:

```json
{
  "tasks": [
    {
      "taskId": "infra_package",
      "type": "infra",
      "dependencies": [],
      "outputFiles": ["package.json"],
      "usesContracts": []
    },
    {
      "taskId": "b_auth",
      "type": "backend",
      "dependencies": ["infra_middleware", "db_tables_user"],
      "outputFiles": ["routes/auth.js", "controllers/authController.js", "services/authService.js"],
      "usesContracts": ["api_auth", "logic_register_user"]
    }
  ]
}
```

**提取规则**:

| 骨架字段 | 写入计划树的哪个列 | 转换规则 |
|---------|------------------|---------|
| `taskId` | §2 映射表 → `sourceTask` | 直接复制（如 `infra_package` → sourceTask=`infra_package`） |
| `type` | §2 映射表 → `layer` | 按类型映射表转换（见下方） |
| `dependencies` | §3 依赖链 + §2 的 dependencies 列 | 纵向: 下层 taskId → 测试层 taskId。横向: 同层前驱 |
| `outputFiles` | §2 映射表 → `targetFiles` | 直接复制。**静态层 targetFiles 可能需要补全**（如 infra 补 .env） |
| `usesContracts` | §2 映射表 → `契约ref` 列 | 直接复制 contractId。接口层/逻辑层必填 |

**type → layer 映射表**:

| 骨架 type | 测试 layer | testType | 说明 |
|-----------|-----------|----------|------|
| `infra` / `infrastructure` | infra | static | 一个骨架 task → 一个测试 task（1:1） |
| `database` / `db` | db | static | 一个骨架 task → 一个测试 task（1:1） |
| `frontend` / `frontend_static` | frontend | static | 一个骨架 task → 一个测试 task（1:1） |
| `backend` | peer_deps + api + db_api + backend_proc | static/interface/logic | 一个骨架 task → 多个测试 task（1:N） |
| `integration` / `integrate` | integ | static | 合并为一个 t_integ |

🛑 **backend 类型 1:N 拆分规则**（最重要）:
- 1 个 backend 骨架 task → 至少 1 个 peer_deps（require 链）+ N 个 api（每个端点 1 个 correct）+ N 个 db_api（每个 DB 操作 1 个 correct）+ N 个 backend_proc（每个 service 函数 1 个）
- `outputFiles` 按层拆分: peer_deps=routes+controllers+services, api=routes+controllers, db_api=services, backend_proc=services
- 每个拆出的 test task 的 sourceTask **都指向同一个骨架 taskId**

---

## 输出格式

`_test_plan_tree.md` 必须包含以下 5 个章节：

### §1 输入摘要

从 4 个输入源提取关键数字，作为后续任务数校验的基线。

```markdown
| 指标 | 值 |
|------|-----|
| 骨架任务总数 | N (infra X + db Y + frontend Z + backend W + integ 1) |
| 预计测试任务总数 | N (静态层 X + 接口层 Y + 逻辑层 Z + 质量层 W) |
| 业务契约 | N scenario + M logic + P api + Q db_api + R model |
| NFR 维度 | 安全/性能/并发/... |
| 核心业务流程 | N 条（主线 X + 运营 Y） |
| 数据实体 | N 个（users, orders, products, ...） |
| 页面数 | N 个页面，M 组相邻跳转 |
```

🛑 **预计测试任务总数必须 ≥ 骨架任务总数**。backend 类型 1:N 拆分 → 测试任务数显著多于骨架任务数。

### §2 逐层映射表（核心产出）

按静态层→接口层→逻辑层→质量层分组，每层一个表格。
**只需映射关系，不需完整 testScenarios/checkPoints。**
但必须包含足够的元数据让后续层 Agent 能独立生成完整 task。

#### 静态层

```markdown
### 静态层

| testId | layer | sourceTask | targetFiles | dependencies | ui_style | 备注 |
|--------|-------|-----------|-------------|-------------|----------|------|
| t_infra_package | infra | infra_package | package.json | — | — | 检查 package.json 结构 |
| t_infra_config | infra | infra_config | config/db.js, config/logger.js | t_infra_package | — | 检查导出 |
| t_infra_middleware | infra | infra_middleware | middleware/auth.js, middleware/permission.js, middleware/errorHandler.js | t_infra_config, t_infra_utils | — | 检查中间件导出 |
| t_db_user | db | db_tables_user | database/schema/users.sql, database/seed/users.json | t_infra_config | — | FK→无（根表） |
| t_db_order | db | db_tables_order | database/schema/orders.sql, database/seed/orders.json | t_db_user | — | FK→users.id |
| (seed 检查已并入各 t_db_* 任务，不单独建 t_db_seed) | — | — | — | — | — | — |
| t_frontend_cart | frontend | f_page_cart | src/pages/cart/index.vue, src/api/cart.js | t_db_cart, t_db_product | cart | v-model→products.fields |
| t_peer_backend_auth | peer_deps | b_auth | routes/auth.js, controllers/authController.js, services/authService.js | t_infra_middleware | — | route→ctrl→svc require链 |
| t_integ | integ | integrate | app.js, src/router/index.js, .env, scripts/init-db.js | t_peer_*, t_infra_app | — | 全链路集成 |
| ... | ... | ... | ... | ... | ... | ... |

🛑 frontend 行的 `ui_style` 必填。从架构师的 scene_tree §4 页面导航表的 `ui_style` 列原样复制。其余层填 只有真正ui列表有相应的但是架构师没填才能补充，文件名就代表了当前文档是给什么场景用的。

🛑 同层依赖写在 dependencies 列中（如 t_db_order 依赖 t_db_user，因为 FK order.user_id→users.id）
🛑 db 表的 FK 链必须全部标出——后续层（db_api/logic）需要知道查询链路
```

#### 接口层

```markdown
### 接口层

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 最少scenario |
|--------|-------|-----------|-------------|-------------|---------|:---:|
| t_auth_token | auth | infra_middleware | middleware/auth.js | t_infra_middleware, t_db_user | auth_bearer_jwt | 3 (correct+error+boundary) |
| t_api_auth | api | b_auth | routes/auth.js, controllers/authController.js | t_frontend_auth, t_dbapi_auth | api_auth | 3 (每端点correct+auth+error) |
| t_api_order | api | b_order | routes/order.js, controllers/orderController.js | t_frontend_order, t_dbapi_order, t_api_auth | api_order | 3 |
| t_dbapi_create_user | db_api | b_auth | services/authService.js | t_db_user | db_api_create_user | ≥3 |
| t_dbapi_order | db_api | b_order | services/orderService.js | t_db_order, t_dbapi_auth | db_api_order | ≥3 |
| t_nav_auth_flow | navigation | f_auth_pages | src/pages/auth/login.vue, src/pages/auth/register.vue, src/pages/auth/reset-password.vue, src/pages/index.vue | t_frontend_auth, t_frontend_home | nav_auth_flow | ≥2 |
| ... | ... | ... | ... | ... | ... | ... |

🛑 api targetFiles = [routes, controllers] 不含 services。db_api targetFiles = [services] 不含 DDL。navigation targetFiles = [pages] 含 router。
🛑 接口层所有任务必须填写契约ref——后续 Agent 根据此列找到对应契约生成 scenario。
🛑 db_api 同层依赖: t_dbapi_auth 先于其他，因为 users 表是所有查询的根。
```

#### 逻辑层

```markdown
### 逻辑层

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 事务数 | 场景摘要 |
|--------|-------|-----------|-------------|-------------|---------|:---:|------|
| t_bp_send_sms_code | backend_proc | b_auth | services/authService.js | t_api_auth, t_dbapi_auth | logic_send_sms_code | 1 | sendSmsCode(phone) → Redis频率→生成→缓存→发送 |
| t_bp_register_user | backend_proc | b_auth | services/authService.js | t_api_auth, t_dbapi_auth, t_bp_send_sms_code | logic_register_user | 1 | registerUser(phone,smsCode,password) → 校验→hash→BEGIN→INSERT users+logs→COMMIT |
| t_logic_create_order | logic | b_order | routes/order.js, controllers/orderController.js, services/orderService.js | t_bp_validate_cart, t_bp_lock_stock | logic_create_order | 2 | 验库存→锁库存→创建订单→扣库存→支付（含补偿回滚） |
| t_scenario_buy | scenario | —（多个） | routes/cart.js, controllers/cartController.js, services/cartService.js, routes/order.js, controllers/orderController.js, services/orderService.js | t_bp_add_to_cart, t_logic_create_order, t_nav_cart_order | sc_buy | 3 交接点 | 加购(cartItemId)→下单(orderId)→支付(paymentNo) |

🛑 契约ref 必须填写——后续 backend_proc/logic/scenario Agent 根据此列找到对应契约生成 process 步骤。
🛑 事务数: 1 → backend_proc。≥2 或含补偿/回滚 → logic。交接点 → scenario。
🛑 **依赖规则**: 
  - backend_proc 依赖 api + db_api
  - **logic 只依赖 backend_proc**（backend_proc 真理封装了全部接口层验证结果）
  - **scenario 只依赖 logic + navigation**（logic 真理 `steps[]` 已聚合函数细节，不需要重复依赖 backend_proc）
```

#### 质量层

```markdown
### 质量层

| testId | layer | sourceTask | targetFiles | dependencies | NFR维度 | 场景摘要 |
|--------|-------|-----------|-------------|-------------|---------|------|
| t_nfr_sql_injection | nfr | — | middleware/sanitizer.js, routes/product.js | t_scenario_shopping | SQL注入 | 搜索+登录注入入口，恶意输入拦截 |
| t_nfr_xss | nfr | — | middleware/sanitizer.js, src/pages/product/detail.vue | t_scenario_shopping, t_nav_browse_flow | XSS | 输出编码，无script标签 |
| t_nfr_concurrency | nfr | — | services/orderService.js | t_scenario_shopping | 并发 | 2并发买最后1件→1成功1冲突 |
| t_nfr_rate_limit | nfr | — | services/authService.js | t_scenario_shopping | 限流 | 超频→429 |
| t_nfr_token | nfr | — | middleware/auth.js | t_auth_token | Token安全 | 过期/伪造token→401 |
| t_nfr_performance | nfr | — | — | t_scenario_shopping | 性能 | k6 压测核心端点 |
| t_nfr_availability | nfr | — | — | t_scenario_shopping | 可用性 | 降级/超时/重试 |
| t_nfr_https | nfr | — | app.js, middleware/ | t_infra_app | HTTPS | 重定向/Secure/HSTS |
| t_nfr_cors | nfr | — | app.js, middleware/ | t_infra_app | CORS | Origin白名单/预检 |

🛑 **NFR 依赖规则**: 端点型(性能/并发/SQL注入/限流/可用性) → **只依赖 scenario**（chains[].endpoints[] 提供全部端点信息）。页面型(XSS) → scenario + navigation。配置型(HTTPS/CORS) → infra。Token安全 → auth。
| ... | ... | ... | ... | ... | ... | ... |

🛑 nfr sourceTask 为 null（横切关注点，不属于单一 sourceTask）。
🛑 NFR 维度 = PRD 声明的维度 + SQL注入 + 限流（兜底）。PRD 有 5 个维度 → nfr≥7。
```

### §3 依赖链

必须列出全部同层和跨层依赖，后续生成 task 时直接抄。

```markdown
## 同层 FK 链（db — 从 model 契约 foreignKeys 提取）

t_db_user → t_db_user_profiles (FK user_id→users.id)
t_db_user → t_db_addresses (FK user_id→users.id)
t_db_user → t_db_merchant (FK user_id→users.id)
t_db_merchant → t_db_product (FK merchant_id→merchants.id)
t_db_categories → t_db_product (FK category_id→categories.id)
t_db_user → t_db_cart (FK user_id→users.id)
t_db_product → t_db_cart (FK product_id→products.id)
t_db_user → t_db_order (FK user_id→users.id)
t_db_order → t_db_payment (FK order_id→orders.id)
t_db_order → t_db_order_items (FK order_id→orders.id)
t_db_payment → t_db_refund (FK payment_id→payments.id)
t_db_order → t_db_review (FK order_id→orders.id)
t_db_product → t_db_review (FK product_id→products.id)
t_db_merchant → t_db_merchant_settlement (FK merchant_id→merchants.id)

## 同层数据依赖（api — api_auth 是所有 api 的前驱，db_api — db_api_auth 是所有 db_api 的前驱）

t_api_auth → t_api_order → t_api_payment → t_api_refund
t_dbapi_auth → t_dbapi_user → t_dbapi_order → t_dbapi_payment

## 同层 infra 配置链

t_infra_package → t_infra_config → t_infra_middleware → t_infra_app

## 跨层依赖

静态层 → 接口层 → 逻辑层 → 质量层
api 依赖 db_api（后端↔数据库契约必须先验证）
logic 依赖 backend_proc（函数级处理链先通过）
scenario 依赖 backend_proc + navigation（需要函数+页面都就绪）
```

### §4 计数校验（先算后写）

**生成完所有映射后，必须逐行核对。任何 ❌ 必须补全。**

```markdown
| 契约类型 | 契约数量（从 _contracts_business.json 统计） | 对应 test task 数量 | 覆盖? |
|---------|:---:|:---:|:---:|
| model | N | X | ✅/❌ |
| api | N | X | ✅/❌ |
| db_api | N | X | ✅/❌ |
| logic | N | X | ✅/❌ |
| navigation（页面相邻组数） | N | X | ✅/❌ |
| scenario | N | X | ✅/❌ |
| infra 子维度（pkg/config/mw/utils/env） | 5 | X | ✅/❌ |
| auth 子维度（token/mw/store/guard） | 4 | X | ✅/❌ |
| NFR 维度（PRD声明 + SQL注入 + 限流） | N+2 | X | ✅/❌ |
| 第三方服务（PRD模块"创新成本"列中标注的模拟/第三方服务） | PRD中标注数 | X | ✅/❌ |
```

### §5 分片计划（若 > 50 个 task）

```markdown
Part 1: t_infra_package ... t_db_refund (N tasks) → 静态层
Part 2: t_auth_token ... t_nav_final (N tasks) → 接口层
Part 3: t_bp_register ... t_scenario_buy (N tasks) → 逻辑层
Part 4: t_nfr_sql ... (N tasks) → 质量层
```

---

## 关键规则

🛑 **targetFiles 按层定义**:
  - infra/db/frontend = 骨架 outputFiles（可能需要补全 .env）
  - peer_deps = routes + controllers + services（同一骨架的）
  - api = routes + controllers（同一骨架的）
  - db_api = services（同一骨架的）
  - navigation = 源页 + 目标页（从页面导航提取）
  - backend_proc = services（同一骨架的，单个函数）
  - logic/scenario = routes + controllers + services（可能跨多个骨架）
  - nfr = 中间件/路由/服务（涉及的防御面）

🛑 **testId 命名**: `t_{layer缩写}_{功能}`，如 `t_api_auth`、`t_bp_order`、`t_dbapi_user`。

🛑 **覆盖审计**：对照 §4 计数表，任何一行 ❌ → 补全映射条目。

🛑 **计数底线（由输入决定, 不达标必须补全）:**
  - auth=1 (固定, 有鉴权就有)
  - api=PRD中主干模块对应的api契约数, db_api=主干模块中涉及DB操作的logic数, navigation=PRD核心业务流程中的页面跳转数
  - backend_proc=logic契约中serviceSignature的函数数, logic=有事务链/补偿/幂等的logic数, scenario=核心业务流程链路数
  - nfr=PRD中NFR维度数+2 (每个维度至少1个测试, +2为SQL注入+限流兜底)
  (原则: 以输入契约和PRD的NFR维度为准, 不是固定数字。PRD有7个NFR维度→nfr≥9, 有3个→nfr≥5)

🛑 **seed 检查已并入各 t_db_* 任务**：不单独建 t_db_seed。每个 db 任务的 targetFiles 含 schema + seed 文件，checkPoints 含 DDL + Seed 两部分。

🛑 **规划树只做映射关系**。具体的 `testScenarios`、`checkPoints` 由后续各层 Agent 填充。

🛑 **每条映射必须有契约ref（接口层/逻辑层）或备注说明（静态层）**。后续 Agent 依赖这些信息定位原始契约/骨架数据。
🛑 **禁止编造 `ui_style`**。静态层 frontend 行的 `ui_style` 只能填 prompt 中注入的「可用 UI 设计文档」列表中的值。文档不存在就填 `?`。

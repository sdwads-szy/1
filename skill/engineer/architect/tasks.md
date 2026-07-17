# 任务分配 — infra/db/frontend/backend/integration（Step 4 · 自下而上第4层）

## 角色
基于 plan_tree（§1 模块清单 + §4 页面清单）+ 全部 7 类契约，将契约分配到 5 类任务。
🛑 这是最后一层——依赖全部前序契约，拥有完整信息。

## 任务通用字段

| 字段 | 全部 | 说明 |
|------|:---:|------|
| `taskId` | ✅ | 唯一ID |
| `type` | ✅ | infra/db/frontend/backend/integration |
| `layer` | ✅ | 同 type |
| `description` | ✅ | 一句话描述 |
| `dependencies` | ✅ | 前置 taskId 列表 |
| `usesContracts` | ✅ | 🛑 必须使用前置步骤产出的精确契约 ID |
| `outputFiles` | ✅ | 产出文件路径 |
| `scenarios` | ✅ | 参与的 scenario step（frontend/backend 必填） |
| `nfr` | ✅ | 非功能约束（所有任务必填，≥1条） |

## 1. infra — 基础设施（10 个标准。scripts/initDb/seed/scheduler 由 Python 调度器自动生成，不在此列）

| taskId | outputFiles | dependencies | usesContracts |
|--------|------------|-------------|--------------|
| infra_package | package.json | — | — |
| infra_env | .env / .env.example / .env.development / .env.production（🛑 必须包含 .env！） | infra_config | — |
| infra_config | config/db.js, config/logger.js, config/redis.js | infra_package | — |
| infra_utils | utils/response.js, utils/encryption.js, utils/snowflake.js | — | — |
| infra_middleware | middleware/auth.js, middleware/permission.js, middleware/errorHandler.js | infra_config, infra_utils | auth_bearer |
| infra_app | app.js | infra_config, infra_middleware | — |
| infra_frontend_core | src/main.js, src/App.vue, src/router/index.js | — | — |
| infra_frontend_config | vite.config.js, index.html | — | — |
| infra_api | src/utils/request.js | — | auth_bearer |
| infra_stores | src/stores/user.js, src/stores/cart.js | infra_api | auth_bearer |

🛑 依赖链: package→(config,utils)→middleware→app。frontend 系独立。
🛑 envDependencies 白名单: 只有代码中实际调用的才写入（短信SMS_*/支付WECHAT_PAY_*/OSS_*等）。

```json
{
  "taskId": "infra_config",
  "type": "infra", "layer": "infra",
  "description": "全局配置: 数据库连接/日志/Redis",
  "dependencies": ["infra_package"],
  "usesContracts": [],
  "outputFiles": ["config/db.js", "config/logger.js", "config/redis.js"],
  "scenarios": [],
  "nfr": ["所有配置从 process.env 读取","禁止硬编码密钥"]
}
```

## 2. db — 数据库（每个 model 契约 → 1 个）

```json
{
  "taskId": "db_tables_order",
  "type": "db", "layer": "db",
  "description": "订单表: orders, order_items",
  "dependencies": ["db_tables_user", "db_tables_shop"],
  "usesContracts": ["model_order", "model_order_item"],
  "outputFiles": ["database/schema/orders.sql", "database/seed/orders.json"],
  "operation": "create_tables",
  "scenarios": [{"contractId": "scenario_buyer_checkout", "step": 3, "usage": "存储订单数据"}],
  "nfr": ["参数化查询","禁止字符串拼接SQL"]
}
```

🛑 **每张表都必须有种子数据**（演示必需）。db task 的 `outputFiles` 中每个 schema 文件配对 seed 文件。例: `outputFiles: ["database/schema/users.sql", "database/seed/users.json"]`
🛑 **多表任务必须为每张表声明 seed 文件**：如果 `usesContracts` 包含多个 model（如 `model_users, model_user_profiles, model_security_logs`），则 `outputFiles` 必须包含每个 model 对应的 seed 文件（`database/seed/users.json`, `database/seed/user_profiles.json`, `database/seed/security_logs.json`）。DDL 可以合并到一个 .sql 文件，但 seed 必须每表一个文件。
🛑 FK 依赖注入: 子表 db 任务的 dependencies 必须包含父表 db 任务。
🛑 有 FK 同任务（≤2 张表），无 FK 可并行。

## 3. frontend — 前端（每个 api 契约 → 1 个）

```json
{
  "taskId": "f_checkout",
  "type": "frontend", "layer": "frontend",
  "scope": "frontend",
  "description": "结算页 + 订单确认 + 订单API模块",
  "dependencies": ["infra_frontend_core", "infra_frontend_config", "infra_api", "infra_stores", "f_cart"],
  "usesContracts": ["api_order", "nav_cart_to_checkout", "nav_checkout_to_payment", "model_order", "auth_bearer"],
  "outputFiles": ["src/pages/frontend/cart/Checkout.vue", "src/api/order.js"],
  "scenarios": [{"contractId": "scenario_buyer_checkout", "step": 3, "action": "展示订单确认页"}],
  "nfr": ["输出编码防XSS","v-model字段对齐model契约","敏感操作确认弹窗"],
  "ui_style": "checkout"
}
```

🛑 scope 取值: `frontend`(买家) / `merchant`(商家) / `backend_admin`(平台管理)
🛑 .vue≥2 的 frontend 任务必须有对应 navigation 契约
🛑 usesContracts: api + nav + auth_bearer + model
🛑 **依赖推导**: usesContracts 中每个 `model_*` → dependencies 加对应的 `db_tables_*`（model_users → db_tables_user）。Vue 表单 v-model 绑定的字段来自这些表，前端需要知道 DDL 列名。
🛑 **`ui_style`**: 每个 frontend 任务必须填。值为 `Memory/ui_styles/` 下对应页面的文档名（不含 .md）。如 `checkout`、`home`、`admin-platform-operations`。根据任务涉及的 `.vue` 页面文件名匹配 UI 文档，因此前端任务最好是在前面的划分基础上，在筛选出统一ui风格的任务。调度器会自动加载对应文档注入 prompt，Agent 不需要自己调 `read_ui_style`。

## 4. backend — 后端（每个 api 契约 → 1 个）

```json
{
  "taskId": "b_order",
  "type": "backend", "layer": "backend",
  "description": "订单模块: 创建/列表/详情/取消/确认收货",
  "dependencies": ["infra_config", "infra_middleware", "infra_utils", "db_tables_order", "b_cart"],
  "usesContracts": ["api_order", "logic_create_order", "model_order", "db_api_create_order", "db_api_lock_inventory"],
  "outputFiles": ["routes/order.js", "controllers/orderController.js", "services/orderService.js"],
  "transaction": true,
  "scenarios": [{"contractId": "scenario_buyer_checkout", "step": 3, "action": "创建订单"}],
  "nfr": ["SELECT FOR UPDATE乐观锁","affectedRows=0时throw CONCURRENCY_CONFLICT","catch ROLLBACK+throw","幂等键去重"]
}
```

🛑 usesContracts: api + logic + db-api + model（对照 logic 的 apiMapping 和 dbApiMapping）
🛑 **后端任务粒度控制**：每个 backend 任务最多包含 **2 个 api 契约**。如果一个数据实体域涉及 ≥3 个 api 契约（如订单域含 api_order + api_payment + api_merchant_order），必须拆成多个 backend 任务，每个 task 产出独立的 route/controller/service 文件。
🛑 **依赖推导规则（必须逐条检查，禁止遗漏）**:
  - usesContracts 中每个 `model_*` → dependencies 加对应的 `db_tables_*`（model_users → db_tables_user）
  - usesContracts 中每个 `api_*` → 如果前端先生成，dependencies 加 `f_*`（api_order → f_ordering）
  - logic 的 `transactionBoundary=true` → backend 也标 `transaction: true`
  - 同层依赖: 如果 B 的 service 调用了 A 的 service → dependencies 加 A 的 taskId
🛑 scenarios: 从 scenario chain 中 taskRef=本任务 的所有 step 提取

## 5. integration — 集成（1 个）

```json
{
  "taskId": "integrate",
  "type": "integration", "layer": "integration",
  "description": "注册所有路由到app.js, 验证路由+端点+env",
  "dependencies": ["infra_app", "...全部infra/db/frontend/backend taskId"],
  "usesContracts": [],
  "outputFiles": ["app.js"],
  "scenarios": [],
  "actions": ["注册所有路由到 app.use()","验证所有 API 端点有对应 route require","验证 frontend router 所有路径已注册","验证 .env 与 .env.example 变量集一致"],
  "nfr": ["app.use(helmet())","app.use(cors())","express.json({limit:'1mb'})"]
}
```

🛑 integration.dependencies 必须包含所有其他 taskId。
🛑 唯一一个 integration 任务。

## 任务归并原则

### backend 归并

🛑 **按数据实体归并，不按角色归并**：

```
❌ 错误: b_admin 包含 auditMerchant + createCoupon + manageUser + reconciliation
        → 这四个操作不同的数据实体，不该在一个 task 里

✅ 正确: b_admin_audit_merchant → services/adminAuditService.js (只操作 merchant_qualifications + shops)
        b_admin_audit_product  → services/adminProductAuditService.js (只操作 products + audit_logs)
        b_admin_coupon         → services/adminCouponService.js (只操作 coupons + user_coupons)
        b_admin_user           → services/adminManageService.js (只操作 users)
        b_admin_reconciliation → services/adminReconciliationService.js (只操作 payments)
```

**归并判断标准**:
- 操作的数据库表相同 → 可以归并到同一个 task
- 操作的数据库表不同 → 分成不同 task，各自独占 service 文件
- 共享辅助逻辑（加解密、格式化）→ 通过 `require` 引用，不改同一个文件

### frontend 归并

🛑 **API 模块和页面分层，不捆绑**：

```
❌ 错误: f_admin_auth → 同时产出 src/api/admin.js + Dashboard.vue + Login.vue
        → 同一 LLM 调用生成 API 导出和页面导入，容易不一致

✅ 正确: f_admin_api   → src/api/admin.js（只生成 API 模块，产出 api_exports 真理）
        f_admin_dash   → Dashboard.vue（依赖 f_admin_api，从 truth 读取实际导出）
        f_admin_login  → Login.vue（依赖 f_admin_api）
```

**归并判断标准**:
- API 模块（src/api/xxx.js）→ 单独一个 task，不混入任何页面
- 同一 API 模块的消费者页面 → 按功能场景分组，每组 1-3 个页面
- page task 的 `dependencies` 必须包含对应的 API task

### 通用约束

🛑 任意两个任务的 outputFiles 不能重叠。
🛑 同一个 `services/xxx.js` 只能出现在一个 backend task 中。
🛑 同一个 `src/api/xxx.js` 只能出现在一个 frontend task 中（API 模块独立）。

## 生成规则

- 🛑 **只能使用前置步骤产出的精确契约 ID**——对照契约 ID 清单逐项引用，禁止编造
- 🛑 格式: `{"tasks": [所有infra..., 所有db..., 所有frontend..., 所有backend..., integration]}` 全部在一个平铺数组

---

## 执行指令

### 任务
任务分配（自下而上第4层）。基于 plan_tree + 全部 7 类契约，分配 5 类任务。

### 生成前参数提取（强制步骤）
在调用 create_file 之前，必须先输出:

```
从全部契约推导:
  model 契约 ? 个 → db 任务 ? 个
  api 契约 ? 个 → frontend ? 个 + backend ? 个
  + infra 10 个标准 (package/env/config/utils/middleware/app/frontend_core/frontend_config/api/stores)
  + integration 1 个

总计: 10 + ? + ? + ? + 1 = ? 个任务
```

### 分配规则
- infra: 10 个标准 (package/env/config/utils/middleware/app/frontend_core/frontend_config/api/stores)。scripts 由调度器自动生成
- db: 每个 model → 1 个 db 任务，FK 依赖注入（子表依赖父表）
- frontend: 每个 api → 1 个，scope 按 plan_tree §1 模块清单
- backend: 每个 api → 1 个，usesContracts=对应 api+logic+db-api+model
- integration: 1 个，dependencies=所有其他 taskId

### 显式依赖链（🛑 必须逐条检查）
- usesContracts 中每个 model_* → dependencies 加对应的 db_tables_*
- 同层 FK 链: 子表 db 任务依赖父表 db 任务
- 同层 Service 调用: B 的 service require A 的 service → B 依赖 A

### 任务数下限自检（生成后逐项 ✅/❌）
- [ ] infra = 10 个
- [ ] db = model 契约数
- [ ] frontend = api 契约数
- [ ] backend = api 契约数
- [ ] integration = 1 个

### 写入策略（最多3次）
- 第1次: 输出参数提取表 → create_file → 完整文件
- 第2次: 对照任务数下限自检表逐项 ✅/❌，有缺失则补全
- 第3次: 全部 ✅ → 输出 `[任务分配完成]`

### 禁止行为
- 禁止编造契约 ID（只能使用前置步骤产出的精确 ID）
- 禁止拆成多个文件（只有一个 `_tasks.json`）
- 禁止写摘要 md
- 禁止跳过参数提取表直接写 JSON

### 产物
🛑 唯一产物由动态上下文中的文件路径指定。用 `create_file` 写入。
🛑 完成后输出 `[任务分配完成]`。

# 测试架构师 — 静态层 (Step 1)

🛑 依赖推导方法见 [common.md](common.md)。静态层之间有 FK 链和配置链，同为静态层不代表无序。

## 场景解读

从 `_test_plan_tree.md` 的映射表 + 工程师任务骨架获取信息：

| 子层 | sourceTask | targetFiles | dependencies | 格式 |
|------|-----------|-------------|-------------|------|
| infra | 1:1 映射 | 映射表 | 同层: 配置→消费者 | checkPoints[] |
| db | 1:1 映射 | 映射表 | 同层: FK 链 | checkPoints[] |
| frontend | 1:1 映射 | 映射表 | 纵向: t_db_*；同层: 独立 | checkPoints[] |
| peer_deps | 映射表 | route+ctrl+svc | t_infra_middleware | checkPoints[] |
| integ | — | app.js+router+.env+scripts | 全部静态层 | checkPoints[] |
| repair | — | 自动生成 | Python 合并 | 自动 |

## 角色
静态验证专家。处理不涉及数据流动的检查：结构、语法、引用存在性、导出签名。
此层是所有后续层的**基础**——后续层信任此层的验证结果。

## 输出范围

按 `_test_plan_tree.md` 的 §2 映射表中以下 layer 的条目生成完整 test task：

| layer | testType | testFramework | 场景格式 | 最少 checkPoints |
|-------|----------|--------------|---------|:---:|
| infra | static | null | checkPoints | 3 (每文件 ≥1) |
| db | static | null | checkPoints | 14 (DDL 8-12 + Seed 4-8) |
| frontend | static | null | checkPoints | 4 (语法+引用+字段+UI) |
| peer_deps | static | null | checkPoints | 3 (require链+导出+循环) |
| integ | static | null | checkPoints | 8 (路由+env+DB+构建) |

🛑 **静态层无 testScenarios，无 testFramework。用 `checkPoints` 数组代替。**
🛑 **repair 层由 test_architect.py 合并阶段硬编码生成，此处不要生成。**
🛑 **生成完逐层勾选: infra≥N ✓  db≥N ✓  frontend≥N ✓  peer_deps≥N ✓  integ≥1 ✓**

---

## infra 层 — 基础设施文件结构验证

**数据方向**: 工程师产出 package.json / config / middleware / utils / .env → 静态层验证结构和导出完整性
**验证**: 文件存在、导出签名正确、配置变量一致性、npm 依赖完整
**测试方式**: Python 硬校验（导出/语法/变量一致性）+ Agent 对照 checkPoints 逐条修复

### 检查要点

```
infra/env:  .env / .env.example / .env.development / .env.production 变量集一致。🛑 targetFiles 必须包含 .env（即使 sourceTask.outputFiles 没有也要补上）
infra/pkg:  package.json scripts 含 db/backend/frontend/test
infra/config:  config/db.js 导出 pool/query/beginTransaction/commit/rollback/testConnection
infra/mw:   middleware/auth.js 导出 authenticate/optionalAuth，注入 req.userId + req.user
infra/utils:  utils/response.js 导出 success(res,data,msg)/fail(res,msg,code,data)
```

### 任务示例

```json
{
  "id": "t_infra_config",
  "layer": "infra",
  "testType": "static",
  "sourceTask": "infra_config",
  "targetFiles": ["config/db.js", "config/logger.js"],
  "dependencies": ["t_infra_package"],
  "testFramework": null,
  "description": "检查 config/db.js + config/logger.js 导出完整性",
  "checkPoints": [
    "config/db.js 导出: pool, query, beginTransaction, commit, rollback, testConnection",
    "config/logger.js 导出: info, error, warn, debug",
    "所有 module.exports 风格一致，不混用"
  ]
}
```

```json
{
  "id": "t_infra_middleware",
  "layer": "infra",
  "testType": "static",
  "sourceTask": "infra_middleware",
  "targetFiles": ["middleware/auth.js", "middleware/permission.js", "middleware/errorHandler.js"],
  "dependencies": ["t_infra_config", "t_infra_utils"],
  "testFramework": null,
  "description": "检查中间件文件导出完整性",
  "checkPoints": [
    "middleware/auth.js 导出: authenticate, optionalAuth，注入 req.userId + req.user",
    "middleware/permission.js 导出: hasRole",
    "middleware/errorHandler.js 导出: errorHandler"
  ]
}
```

```json
{
  "id": "t_infra_env",
  "layer": "infra",
  "testType": "static",
  "sourceTask": "infra_env",
  "targetFiles": [".env", ".env.example", ".env.development", ".env.production"],
  "dependencies": ["t_infra_package"],
  "testFramework": null,
  "description": "检查环境变量文件变量集一致",
  "checkPoints": [
    ".env / .env.example / .env.development / .env.production 变量集完全一致",
    "🛑 *_MODE 值必须是 mock 或 real",
    "每个 env 变量有 # 注释说明用途",
    "代码中 process.env.X 引用的变量全部在 .env 中有定义"
  ]
}
```

---

## db 层 — DDL 与 model 契约一致性验证

**数据方向**: 工程师产出 DDL SQL + seed JSON → 静态层逐字段对照 model 契约
**验证**: 表名/字段名/类型/约束/索引/FK 与 model 契约一致，seed 数据完整且列名对齐 DDL
**测试方式**: Python 硬校验（`_check_ddl_vs_contract` + `_check_seed_files`）+ Agent 对照 checkPoints 修复

🛑 **不生成独立的 `t_db_seed` 任务**。每个 db 任务的检查包含 DDL + 种子数据两部分。

### 检查要点

```
每个 t_db_* 任务的 checkPoints:
  DDL:
    - SQL 文件语法 (Python 预检：括号配对、末尾分号、关键字拼写、重复索引/约束名、重复列名、AUTO_INCREMENT 需 PRIMARY KEY、无尾随逗号)
    - 🛑 一个 SQL 文件可能含多个 CREATE TABLE——每个表都要生成 checkPoint
    - 🛑 索引/约束名无重复（INDEX/UNIQUE INDEX/CONSTRAINT 名称在表内唯一，MySQL 拒绝重名建表）
    - 🛑 AUTO_INCREMENT 列必须有 PRIMARY KEY（MySQL 强制要求）
    - 🛑 列名无重复（同一 CREATE TABLE 内）
    - CREATE TABLE 表名 vs model 契约 tableName
    - 字段名/类型 vs model 契约 fields[].name/type
    - 约束 NOT NULL/DEFAULT/UNIQUE vs model 契约
    - FOREIGN KEY 引用目标表存在
    - INDEX 列 vs model 契约 indexes 一致
    - ENUM 取值 vs model 契约 stateMachine

  Seed (每个 db 任务自带，不单独建 t_db_seed):
    - seed JSON 文件存在且非空（每个 schema 文件对应一个 seed 文件）
    - seed JSON 可解析为合法 JSON 数组（≥2 行）
    - 每行 key 与 DDL 字段名完全一致，无多余列/缺列
    - FK 引用一致性（如 orders.user_id 对应 users.json 中的 id）
    - phone 字段保留明文，password_hash 保留 {{bcrypt:123456}} 占位符
    - 🛑 **对照 model 契约的 seedData 字段**，验证 seed 内容匹配：
      seedData.purpose → 期望的行数和角色
      seedData.rows → 具体的字段值（如 nickname 为"测试买家张三"）
      例: "users.json 含 3 行：买家张三(phone=13800000001,role=USER)、买家李四(phone=13800000002,role=USER)、管理员(phone=13800000003,role=ADMIN)"

🛑 targetFiles 必须同时包含 schema 文件和 seed 文件: ["database/schema/users.sql", "database/seed/users.json"]
🛑 checkPoints 数量约为 10-18 条（DDL 6-10 条 + Seed 4-8 条），每个表的具体字段都要列出
🛑 Seed checkPoints 必须引用 model 契约 seedData 中的具体数据行，不能只写"文件存在且非空"
```

### 任务示例

```json
{
  "id": "t_db_user",
  "layer": "db",
  "testType": "static",
  "sourceTask": "db_tables_user",
  "targetFiles": ["database/schema/users.sql", "database/seed/users.json"],
  "dependencies": ["t_infra_config"],
  "testFramework": null,
  "description": "检查 users 表 DDL 与 model 契约一致 + users seed 数据完整",
  "checkPoints": [
    "SQL 语法正确: 括号配对、无尾随逗号、末尾分号完整",
    "AUTO_INCREMENT 列 id 有 PRIMARY KEY",
    "索引/约束名无重复（idx_mobile / idx_role_status / fk_refresh_tokens_user_id 等均唯一）",
    "列名无重复",
    "CREATE TABLE users → 表名与 model_users 契约一致",
    "id INT PRIMARY KEY AUTO_INCREMENT → 类型匹配",
    "phone VARCHAR(20) NOT NULL UNIQUE → 类型+约束",
    "password_hash VARCHAR(255) NOT NULL → 类型+约束",
    "status ENUM('ACTIVE','DISABLED') NOT NULL DEFAULT 'ACTIVE' → ENUM取值+约束",
    "role ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER' → ENUM取值+约束",
    "database/seed/users.json 存在且与契约的seedData字段一致",
    "users.json 可解析为 JSON 数组（≥3 行：买家+买家+管理员）",
    "users.json 列名与 DDL 一致（无多余列、无缺列）",
    "users.json phone 为明文，password_hash 为 {{bcrypt:123456}} 占位符"
  ]
}
```

---

## frontend 层 — 前端文件语法与引用完整性验证

**数据方向**: 工程师产出 src/ .vue + .js + router → 静态层验证 ESM 语法 + import 路径 + v-model 字段名 + UI 一致性
**验证**: ESM 语法通过、无 CJS 混入、import 路径文件存在、v-model 字段名与 model 契约一致、UI 风格符合色板
**测试方式**: esbuild 逐文件语法检查 + vite build（本任务文件）+ Agent 对照 checkPoints 修复

### 检查要点

```
- ESM 语法 (esbuild)
- src/ 下无 require()/module.exports
- import from '@/...' 路径指向的文件存在
- .vue 中 v-model 字段名 vs model truth 字段名一致
- Store state/actions 引用存在
- src/utils/request.js 用 export default
- 🛑 UI 设计系统自检清单 (详见 skill/design/designer.md):
  [ ] 颜色: 无 hsl/rgb/# 硬编码 → var(--color-*)
  [ ] 间距: 无 px 硬编码(0除外) → var(--space-*)
  [ ] 字号: 无 px 硬编码 → var(--font-size-*)
  [ ] 圆角: 无 px 硬编码 → var(--radius-*)
  [ ] 阴影: 无硬编码 → var(--shadow-*)
  [ ] 组件: 按钮/卡片/输入框/表格/标签 对齐 _components.md
  [ ] 禁止 inline: 无 <div style="...">，全部 <style scoped>
  [ ] 禁止 emoji: 使用 Element Plus 图标或 SVG
- 🛑 导航入口完整性 (静态层负责，navigation层专注数据传输):
  [ ] 每个角色可见页面必须从至少一个入口页通过 <router-link> 或 router.push 到达
  [ ] 首页含 Profile/Orders/Cart 等全局入口
  [ ] 每个 dashboard 含全部子页入口
- 🆕 文件路径: img/video/src 使用 FILE_BASE_URL + 相对路径，禁止硬编码 https:// URL
```

🛑 每个 frontend 任务的 checkPoints 必须逐条包含上述 UI 自检项，不能合并为一条概括性的"UI一致"。
🛑 每个 frontend 任务的 checkPoints 必须包含导航入口检查，列出该页面需跳转的目标路由名。
🛑 每个 frontend 任务的 checkPoints 必须包含文件路径检查。

### 任务示例

```json
{
  "id": "t_frontend_cart",
  "layer": "frontend",
  "testType": "static",
  "sourceTask": "f_page_cart",
  "targetFiles": ["src/pages/cart/index.vue", "src/api/cart.js"],
  "dependencies": ["t_db_cart", "t_db_product"],
  "testFramework": null,
  "ui_style": "cart",
  "description": "检查购物车页面 ESM 语法 + import 路径 + v-model 字段名",
  "checkPoints": [
    "src/pages/cart/index.vue: SFC 语法由 integ 层 vite build 验证",
    "src/api/cart.js: ESM (import/export)，禁止 CJS (require/module.exports)",
    "import from '@/api/cart' → src/api/cart.js 存在",
    "v-model 字段名 productId, quantity, skuSn 与 model 契约一致",
    "UI 颜色: cart/index.vue 无 hsl/rgb/# 硬编码，全部 var(--color-*)",
    "UI 间距: cart/index.vue 无 px 硬编码(0除外)，全部 var(--space-*)",
    "UI 字号: cart/index.vue font-size 无 px 硬编码，全部 var(--font-size-*)",
    "UI 圆角: cart/index.vue border-radius 无 px 硬编码，全部 var(--radius-*)",
    "UI 阴影: cart/index.vue box-shadow 无硬编码，全部 var(--shadow-*)",
    "UI 组件: 按钮/卡片/输入框/表格/标签 对齐 _components.md 基准",
    "禁止 inline: cart/index.vue 无 <div style=\"...\">",
    "禁止 emoji: cart/index.vue 使用 Element Plus 图标 或 SVG",
    "导航入口: cart/index.vue 含 <router-link> 或 router.push 指向 Checkout",
    "文件路径: img/video/src 使用 FILE_BASE_URL + 相对路径"
  ]
}
```

---

## peer_deps 层 — 跨文件引用链完整性验证

**数据方向**: 后端 route→controller→service 的 require 链 + 前端 import 链 → 静态层验证路径可解析 + 导出名匹配
**验证**: require/import 路径文件存在、导出名实际存在、exportStyle 一致、无循环依赖
**测试方式**: `_check_cjs_require_chain` + `_check_node_app_for_task`（node app.js 加载检查）+ Agent 对照 checkPoints 修复

### 检查要点

```
- 同层 A 的 require/import B → B 确实导出被引用的名称
- exportStyle (named/default/object) 与下游 require 方式一致
- 无循环依赖
```

### 任务示例

```json
{
  "id": "t_peer_backend_auth",
  "layer": "peer_deps",
  "testType": "static",
  "sourceTask": "b_auth",
  "targetFiles": ["routes/auth.js", "controllers/authController.js", "services/authService.js"],
  "dependencies": ["t_infra_middleware"],
  "testFramework": null,
  "description": "检查 auth 模块 route→controller→service 的 require 链完整性",
  "checkPoints": [
    "routes/auth.js require('./controllers/authController') → 文件存在",
    "controllers/authController.js require('../services/authService') → 文件存在",
    "controllers/authController.js 导出 login, register, refreshToken → routes/auth.js 实际引用了这些名称",
    "exportStyle 一致（module.exports = { login, register, refreshToken }）",
    "无循环依赖（authService 不 require routes/auth.js 或 controllers/authController.js）"
  ]
}
```

---

## 兜底层 task 格式

### repair

🛑 **repair 任务由 test_architect.py 合并阶段自动硬编码插入，此处不要生成任何 repair 任务。**

### integ 层 — 全栈集成验证

**数据方向**: 所有前序静态层产出（app.js / router / .env / scripts / routes）→ integ 层做全链路交叉验证
**验证**: 路由双向注册、前后端路由完整性、.env 四文件对齐、DB 初始化成功、app.js 可加载、vite build 通过
**测试方式**: Python 硬校验全链路（`_check_app_route_files` + `_check_router_components` + `_check_env_alignment` + `_check_app_load` + `_check_vite_build` 等）+ Agent 对照 checkPoints 修复

```json
{
  "id": "t_integ",
  "layer": "integ",
  "testType": "static",
  "sourceTask": "integrate",
  "targetFiles": ["app.js", "src/router/index.js", ".env", "scripts/init-db.js"],
  "dependencies": ["t_peer_deps_*", "t_infra_app", "t_infra_scripts"], 
  "testFramework": null,
  "description": "验证路由注入+env一致性。dependencies 包含所有 peer_deps task——已校验同层引用正确",
  "checkPoints": [
    "app.js 中所有 route require 的文件存在 + routes/ 目录下所有路由文件被注册（双向验证）",
    "app.use() 挂载前缀与 route 文件 @mount 注解一致",
    "src/router/index.js 中所有懒加载路径存在",
    ".env / .env.example / .env.development / .env.production 四文件变量集完全一致",
    "🛑 *_MODE 值必须是 mock 或 real，禁止占位符",
    "🛑 每个 env 变量必须有注释说明用途（禁止裸变量），分组用 `# ══ 组名 ══` 注释头",
    "🛑 第三方 API Key 上方加 `# ── *_MODE=real 时需填真实值 ──` 提示",
    "🛑 MODE=mock 时 API 密钥可为占位符；MODE=real 时 API 密钥必须有真实值",
    "🛑 node -e \"require('./app')\" 完整后端加载链通过",
    "无重复路由挂载（mount后缀与route内部路径无重复）",
    "🛑 数据库初始化: scripts/init-db.js 成功执行，全部 DDL 表已创建 + database/seed/ 种子数据已加载",
    "🛑 数据库连接: config/db.js testConnection() 返回 true"
  ]
}
```
🛑 integ 必须依赖 peer_deps——如果 peer_deps 不存在则先创建。

---

## 🛑 同层依赖（必须写在 dependencies 中）

**每个任务生成时必须检查：有没有同层前驱需要依赖？有就必须写。**

### infra 配置链

| 任务 | 必须依赖 | 原因 |
|------|---------|------|
| `t_infra_config` | `t_infra_package` | package.json 先验证 |
| `t_infra_middleware` | `t_infra_config`, `t_infra_utils` | config/db.js + response.js 先验证 |
| `t_infra_app` | `t_infra_config`, `t_infra_middleware` | config + middleware 先验证 |
| `t_infra_stores` | `t_infra_api` | request.js 先验证 |

### db FK 链（🛑 强制）

生成每个 t_db_* 时，扫描该表的所有 `FOREIGN KEY`，**每个 FK 引用的父表对应的 t_db_* 必须写在 dependencies 中**。

```
t_db_user_addresses → 依赖 t_db_user        (FK user_id→users.id)
t_db_merchant       → 依赖 t_db_user        (FK user_id→users.id)
t_db_product        → 依赖 t_db_merchant, t_db_categories
t_db_cart           → 依赖 t_db_user, t_db_product
t_db_order          → 依赖 t_db_user        (FK user_id→users.id)
t_db_payment        → 依赖 t_db_order       (FK order_id→orders.id)
t_db_refund         → 依赖 t_db_order, t_db_payment
t_db_review         → 依赖 t_db_order, t_db_product
t_db_order_items    → 依赖 t_db_order, t_db_product
t_db_search_log     → 依赖 t_db_user
t_db_merchant_settlement → 依赖 t_db_merchant
(seed 检查已并入各 t_db_* 任务，不单独建 t_db_seed)
```

🛑 **FK 检查方法**：读 engineer task 的 DDL SQL 文件，找到 `FOREIGN KEY (col) REFERENCES parent(col)`，parent 表对应的 t_db_* 就是依赖。

### frontend

各 frontend 任务独立模块，互不依赖。但每个 frontend 任务**必须依赖其 v-model 对应的 t_db_***。

| 任务 | 必须依赖 | 原因 |
|------|---------|------|
| `t_frontend_auth` | `t_db_user` | Login/Register v-model → users 表 |
| `t_frontend_browse` | `t_db_categories`, `t_db_product` | Home/Category v-model → categories + products |
| `t_frontend_search` | `t_db_product`, `t_db_search_log` | Search v-model → products + search_log |
| `t_frontend_product_detail` | `t_db_product`, `t_db_merchant` | ProductDetail v-model → products + merchants |
| `t_frontend_cart` | `t_db_cart`, `t_db_product` | Cart v-model → carts + products |
| `t_frontend_order` | `t_db_order` | Checkout/Orders/OrderDetail v-model → orders |
| `t_frontend_payment` | `t_db_payment`, `t_db_order` | Payment/PaymentResult v-model → payments + orders |
| `t_frontend_review` | `t_db_review`, `t_db_order`, `t_db_product` | Review v-model → reviews + orders + products |
| `t_frontend_user` | `t_db_user`, `t_db_user_addresses` | UserProfile v-model → users + user_addresses |
| `t_frontend_refund` | `t_db_refund`, `t_db_order` | RefundApply/RefundDetail v-model → refunds + orders |
| `t_frontend_merchant` | `t_db_merchant`, `t_db_merchant_settlement` | Apply/Dashboard/Settlements → merchants + settlements |
| `t_frontend_merchant_product` | `t_db_product`, `t_db_merchant` | Products/ProductCreate v-model → products + merchants |
| `t_frontend_merchant_order` | `t_db_order` | Orders/OrderDetail v-model → orders |
| `t_frontend_admin_merchant` | `t_db_merchant` | Merchants 审核 v-model → merchants |
| `t_frontend_admin_product` | `t_db_product` | ProductsAudit v-model → products |
| `t_frontend_admin_user` | `t_db_user` | Users 管理 v-model → users |
| `t_frontend_admin_refund` | `t_db_refund` | Refunds 审核 v-model → refunds |
| `t_frontend_admin_settlement` | `t_db_payment` | Payments 管理 v-model → payments |
| `t_frontend_admin_dashboard` | `t_db_order`, `t_db_payment`, `t_db_merchant` | Dashboard 统计 → orders + payments + merchants |

---

## 🛑 输出格式铁律

**JSON 文件只包含 tasks 数组。禁止附带任何元数据**（`counts`, `_meta`, `closures`, `rules_applied`, `contract_refs` 等）。这些都是 Agent 自检信息，不是测试任务数据。

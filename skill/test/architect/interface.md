# 测试架构师 — 接口层 (Step 2)

🛑 **生成前必读: 接口层含 4 个子层，必须全部生成，缺一不可。**
🛑 **生成顺序: auth → db_api → api → navigation。每层生成完检查任务数达标后再进入下一层。**

## 场景解读

🛑 依赖推导方法见 [common.md](common.md) 的纵向 4 问 + 横向 3 问。本节只讲各层的场景字段具体怎么填。

从 `_test_plan_tree.md` 的接口层映射表 + `_scene_tree.md` 的契约拿到：
- `sourceTask` → 从映射表的 sourceTask 列取
- `targetFiles` → 按层规则（api=routes+controllers, db_api=services, navigation=源页+目标页）
- `dependencies` → 纵向：依赖的下层任务 ID；横向：同层前驱任务 ID
- `testScenarios` → 每个契约端点/sql操作/跳转对至少 1 个 scenario

---

## 角色
接口验证专家。验证数据穿过系统边界时**格式/字段是否与契约一致**。不关心数据含义和处理逻辑，只关心"传过去的东西对不对"。

场景格式: **input(输入) + output(期望输出)**。不需要 process 步骤链。

## 输出范围

按 `_test_plan_tree.md` 的 §2 映射表中的接口层条目生成完整 test task。

🛑 **必须生成全部 4 层——缺一不可：**

| layer | testType | testFramework | 最少 scenario | 预计任务数 |
|-------|----------|--------------|:---:|:---:|
| auth | interface | jest | 3 (correct+error+boundary) | 1 |
| api | interface | jest | ≥3 (每端点1correct+auth+error) | ~19 |
| db_api | interface | jest | ≥3 (每SQL操作1correct+≥1error) | ~19 |
| navigation | interface | jest | ≥2 (每相邻页面组) | ~10 |

🛑 **生成完逐层勾选: auth≥1 ✓  api≥19 ✓  db_api≥19 ✓  navigation≥8 ✓**

## auth 层 — JWT Token 纯直调验证

**数据方向**: JWT 库调用 → 中间件行为 → 前端存储
**验证**: jwt.sign/jwt.verify 的 payload 字段、过期行为、中间件注入 req.userId、前端 localStorage key
**测试方式**: **纯 JWT 直调**（`jwt.sign` + `jwt.verify`），**不调 HTTP**。中间件/存储/守卫用静态检查（`fs.readFileSync`）。

🛑 **auth 层铁律: 纯 JWT 直调，禁止 HTTP**。
🛑 **禁止 `require('supertest')`**、**禁止 `require('../../app')`**。
🛑 refresh token 端点测试（POST /api/auth/refresh）→ 归入 **api 层**，不是 auth 层。

### auth scenario 类型

| category | 验证内容 | 示例 |
|----------|---------|------|
| correct | jwt.sign 产出合法 token，payload 字段正确 | `jwt.sign({userId:1, role:'buyer'}, SECRET)` → 三段式 base64 |
| error | 过期/tampered token 被拒绝 | `jwt.sign({...}, SECRET, {expiresIn:'0s'})` → TokenExpiredError |
| boundary | 无 Authorization header → 401 | `authenticate(req)` 中 `req.headers.authorization` 为 undefined |

🛑 auth scenario 必填 `category`（correct/error/boundary），缺少 category 会导致 B/D 步骤无法正确诊断。**至少 3 个 scenario: correct + error + boundary**。

### auth 检查维度

```
auth/token:  jwt.sign/verify, payload 字段, 过期行为
auth/mw:     authenticate 注入 req.userId + req.user, 无 token 返回 401
auth/store:  localStorage key 为 auth_token, Authorization header 格式 Bearer {token}
auth/guard:  router 中 requiresAuth/requiresAdmin 存在（fs.readFileSync 静态检查）
```

### auth 任务示例

```json
{
  "id": "t_auth_token",
  "layer": "auth",
  "testType": "interface",
  "sourceTask": "infra_middleware",
  "targetFiles": ["middleware/auth.js"],
  "dependencies": ["t_infra_middleware", "t_db_user"],
  "testFramework": "jest",
  "description": "JWT 直调验证 token 格式/payload/过期 + 中间件注入",
  "note": "来自 auth_bearer_jwt 契约，纯 JWT 直调不涉及 HTTP",
  "testScenarios": [
    {
      "scenario": "jwt.sign 产出三段式 token",
      "category": "correct",
      "input": "jwt.sign({userId:1, role:'buyer'}, JWT_SECRET)",
      "output": "token.split('.').length === 3, 每段合法 base64"
    },
    {
      "scenario": "过期 token 被 jwt.verify 拒绝",
      "category": "error",
      "input": "jwt.sign({userId:1}, JWT_SECRET, {expiresIn:'0s'})",
      "output": "jwt.verify() throws TokenExpiredError"
    },
    {
      "scenario": "无 Authorization header → authenticate 返回 401",
      "category": "boundary",
      "input": "请求不含 Authorization header",
      "output": "authenticate 返回 401, 不注入 req.userId"
    }
  ]
}
```

🛑 auth 任务 targetFiles 只含 `middleware/auth.js`。token 配置（JWT_SECRET）从 .env 读取，DDL 列名从 t_db_* 真理获取。
🛑 auth 任务必须依赖 `t_infra_middleware`（中间件已验证导出）+ `t_db_user`（users 表已验证）。

## api 层 — 前端↔后端接口契约验证

**数据方向**: 前端 `src/api/*.js` 发送 HTTP 请求 → 后端 `routes/*.js` 接收
**验证**: 前端调用的 method+path+body字段 与后端路由定义/controller参数/响应格式 **静态契约一致**
**测试方式**: `fs.readFileSync` 读取前端 API 文件 + 后端路由/controller 文件，**禁止 supertest，禁止 HTTP，禁止 DB 连接**

### 4 类验证集

| 验证集 | 场景 | 示例 |
|--------|------|------|
| correct | 前端调用路径+方法+字段 = 后端路由+controller | `src/api/order.js: request.post('/api/orders', {items})` → `routes/order.js: router.post('/orders', ...)` |
| error | 错误码映射存在 | controller 中 catch 块有 errorMap/switch |
| auth | 路由挂载了 authenticate/hasRole | `router.{method}(path, authenticate, hasRole('admin'), handler)` |

🛑 **api 层铁律: 每个端点至少 1 个 correct scenario + 1 个 auth scenario + 1 个 error scenario。缺一不可。**
🛑 每个模块 1 个 task，该模块有几个 HTTP 端点 task 就有几个 correct scenario。
🛑 admin 接口必须有 auth(含 hasRole) + error(含错误码映射)，不能只有 correct。
🛑 **api 任务必须依赖前端 API 任务**（`t_frontend_api_*`）+ **对应 db_api 任务**。前端是权威数据源，db_api 确保后端↔数据库契约已通过后再验证前端↔后端。

### 🛑 生成前必须先输出参数提取表（与 logic 层相同规则）

**契约是唯一权威来源。api 层的 route/handler/middleware/request.fields 必须从 api 契约原文复制，禁止自己编造。**

```
对每个 api 任务，先找到对应的 api 契约（contractId），逐字段抄：

## 参数提取: {task_id} ← 契约 {contractId}

端点列表（从 endpoints[] 逐字段抄）:
  endpoint1: {method} {path} → frontendFunction: {name}
              middlewareChain: [{mw1}, {mw2}, ...]
              request.fields: [{name}, {name}, ...]
  endpoint2: ...
  ...

错误码（从 errorMapping 逐字抄 key）:
  {key1}, {key2}, ...
```

**然后写 JSON 时，output.route 中的 method/path/handler 必须与上表逐字一致。禁止编造不存在的端点（如契约没有 /select-all 就不要写 /select-all）。**

### 场景格式

```json
{
  "id": "t_api_cart",
  "layer": "api",
  "testType": "interface",
  "sourceTask": "b_cart",
  "targetFiles": ["routes/cart.js", "controllers/cartController.js", "src/api/cart.js"],
  "dependencies": ["t_frontend_cart", "t_dbapi_cart", "t_api_auth"],
  "testFramework": "jest",
  "description": "验证前端 src/api/cart.js 的 HTTP 调用与后端 routes/cart.js + cartController.js 的契约一致",
  "note": "🛑 契约 api_cart。endpoints: POST / → addToCart, GET / → listCart, PUT /:id → updateCartItem, DELETE /:id → removeCartItem, POST /select → selectForCheckout, GET /summary → getCartSummary",
  "_trace": {"from": "contract", "contractId": "api_cart", "basePath": "/api/cart"},
  "testScenarios": [
    {
      "scenario": "POST / → routes匹配 + fields一致",
      "category": "correct",
      "input":  {"src": "src/api/cart.js"},
      "output": {"route": "router.post('/', authenticate, addToCart)", "ctrl": "req.body 解构 productId, skuSn, quantity"}
    },
    {
      "scenario": "GET / → routes匹配",
      "category": "correct",
      "input":  {"src": "src/api/cart.js"},
      "output": {"route": "router.get('/', authenticate, listCart)"}
    },
    {
      "scenario": "PUT /:id → routes匹配 + body字段",
      "category": "correct",
      "input":  {"src": "src/api/cart.js"},
      "output": {"route": "router.put('/:id', authenticate, updateCartItem)", "ctrl": "req.params.id + req.body.quantity, version"}
    },
    {
      "scenario": "DELETE /:id → routes匹配",
      "category": "correct",
      "input":  {"src": "src/api/cart.js"},
      "output": {"route": "router.delete('/:id', authenticate, removeCartItem)"}
    },
    {
      "scenario": "POST /select → routes匹配",
      "category": "correct",
      "input":  {"src": "src/api/cart.js"},
      "output": {"route": "router.post('/select', authenticate, selectForCheckout)", "ctrl": "req.body 解构 selected"}
    },
    {
      "scenario": "GET /summary → routes匹配",
      "category": "correct",
      "input":  {"src": "src/api/cart.js"},
      "output": {"route": "router.get('/summary', authenticate, getCartSummary)"}
    },
    {
      "scenario": "auth — 全部路由挂载 authenticate",
      "category": "auth",
      "input":  {"src": "src/api/cart.js"},
      "output": {"route": "所有路由含 authenticate 中间件"}
    },
    {
      "scenario": "controller 错误码映射",
      "category": "error",
      "input":  {"src": "src/api/cart.js"},
      "output": {"ctrl": "catch 块含 errorMap"}
    }
  ]
}
```

🛑 接口层 scenario 必填: `input` + `output` + `category`。
🛑 api 层 category: correct(路由+字段匹配), error(错误码映射), auth(中间件链)
🛑 **output.route 中的 method/path/handler 从契约 endpoints 逐字段抄。契约写 POST /select → selectForCheckout 就写 POST /select → selectForCheckout，禁止写成 PUT /select-all → selectAll。**
🛑 targetFiles 必须包含前端 `src/api/*.js` 文件

### 🛑 同层依赖（必须写在 dependencies 中）

#### api 同层

| 任务 | 必须依赖 | 原因 |
|------|---------|------|
| `t_api_auth` | —（第一个） | 鉴权接口先验证 |
| 其余所有 `t_api_*` | `t_api_auth` | token 格式已验证，其余 api 信任鉴权 |

🛑 **每个 api 任务（除 t_api_auth 外）的 dependencies 必须包含 `t_api_auth`**。

#### db_api 同层

| 任务 | 必须依赖 | 原因 |
|------|---------|------|
| `t_dbapi_auth` | —（第一个） | users 表先验证 |
| 其余所有 `t_dbapi_*` | `t_dbapi_auth` | users 表列名已验证，其余信任 |

🛑 **每个 db_api 任务（除 t_dbapi_auth 外）的 dependencies 必须包含 `t_dbapi_auth`**。

## db_api 层 — SQL 列名对齐 DDL

**数据方向**: Service 层 SQL 语句 → 数据库 DDL 定义
**验证**: SQL 中引用的列名/表名在 DDL 中存在，INSERT 列数=VALUES 数，类型匹配
**测试方式**: fs.readFileSync(DDL) 读取表定义，与 Service SQL 中的列名逐项 toContain 比对

🛑 **每个模块 1 个 db_api task，每个 SQL 操作 1 个 scenario**。service 文件中有几个 SQL 操作，task 就有几个 correct scenario（+ 至少 1 个 error + 至少 1 个 boundary）。
🛑 db_api 全静态（fs.readFileSync），不存在并发写冲突，scenario 多点不影响稳定性。
🛑 targetFiles 只含 service 文件。DDL 字段信息通过 t_db_* 真理获取，不需要放入 targetFiles。

### db_api scenario 类型

| category | 验证内容 | 示例 |
|----------|---------|------|
| correct | SQL 列名在 DDL 中存在 | `expect(ddl).toContain('phone')` |
| error | 编造不存在的列名 | `expect(ddl).not.toContain('xyz_not_a_column')` |
| boundary | NOT NULL / PRIMARY KEY / FK 约束 | `expect(ddl).toMatch(/PRIMARY KEY/)`, `expect(ddl).toContain('NOT NULL')` |

🛑 **每个 db_api task 至少 1 个 boundary scenario**：检查目标表至少 1 个必填列有 NOT NULL、有 PRIMARY KEY、有 FOREIGN KEY 引用。

```json
{
  "id": "t_dbapi_create_user",
  "layer": "db_api",
  "testType": "interface",
  "sourceTask": "b_auth",
  "targetFiles": ["services/authService.js"],
  "dependencies": ["t_db_users"],
  "testFramework": "jest",
  "description": "验证 authService.createUser 的 INSERT INTO users 列名在 DDL 中存在",
  "note": "🛑 authService 有 10 个 SQL 操作 → 至少 10 个 correct scenario + 2 个 error scenario",
  "testScenarios": [
    {
      "scenario": "INSERT INTO users — 列名对齐",
      "category": "correct",
      "input":  {"func": "authService.createUser", "sql": "INSERT INTO users", "columns": ["phone", "password_hash", "nickname", "avatar", "role", "status"]},
      "output": {"columns": ["phone", "password_hash", "nickname", "avatar", "role", "status"], "expect": "全部在 DDL 中存在（DDL 来自 t_db_users 真理）"}
    },
    {
      "scenario": "SELECT FROM users WHERE phone — 列名对齐",
      "category": "correct",
      "input":  {"func": "authService.findUserByPhone", "sql": "SELECT", "columns": ["id", "phone", "password_hash", "nickname", "avatar", "role", "status"]},
      "output": {"columns": ["id", "phone", "password_hash", "nickname", "avatar", "role", "status"], "expect": "全部在 DDL 中存在"}
    },
    {
      "scenario": "INSERT INTO user_logs — 列名对齐",
      "category": "correct",
      "input":  {"func": "authService.insertLoginLog", "sql": "INSERT INTO user_logs", "columns": ["user_id", "action", "ip", "user_agent"]},
      "output": {"columns": ["user_id", "action", "ip", "user_agent"], "expect": "全部在 DDL 中存在（DDL 来自 t_db_user_logs 真理）"}
    },
    {
      "scenario": "编造列名 — 'username' 不在 DDL 中",
      "category": "error",
      "input":  {"func": "authService", "columns": ["username"]},
      "output": {"expect": "username 不在 DDL 字段列表中"}
    }
  ]
}
```
🛑 每个 correct scenario: input.columns = service 源码中的列名列表，output.expect = 全部应在 DDL 中存在（DDL 列名通过 t_db_* 真理获取，不需要写死文件名）。

检查要点：
```
- SQL 列名在 DDL 中存在
- INSERT 列列表数量 = VALUES 占位符数量
- 事务内使用 conn.execute() 而非 db.query()
- 操作类型与契约声明一致 (CRUD_CREATE→INSERT, CRUD_READ→SELECT)
```

## navigation 层 — 页面跳转参数传递

**数据方向**: 页面 A 跳转 → 页面 B，参数在路由间传递
**验证**: passBy 方式与契约一致，参数名一致，目标路由存在

🛑 **navigation 按页面跳转相邻关系分组**，不是按角色守卫。每层相邻页面组成一个 task。

### 任务拆分规则

按导航图分层遍历，相邻页面成组（A↔B 同一 task，防止循环依赖）：

```
t_nav_auth_flow:        Login ↔ Register ↔ ResetPassword ↔ Home
t_nav_browse_flow:      Home ↔ Categories ↔ ProductList ↔ ProductDetail ↔ Search
t_nav_cart_order:       ProductDetail ↔ Cart ↔ OrderCreate ↔ OrderList ↔ OrderDetail
t_nav_payment:          OrderDetail ↔ Payment
t_nav_user:             Home ↔ Profile ↔ Addresses
t_nav_refund:           OrderDetail ↔ RefundApply ↔ RefundDetail
t_nav_merchant:         Apply ↔ Status ↔ Products ↔ Orders ↔ Stats
t_nav_merchant_editor:  Products ↔ Create ↔ Edit
t_nav_admin_core:       Users ↔ Merchants ↔ ProductsAudit ↔ Categories
t_nav_admin_ops:        Orders ↔ Refunds ↔ Search ↔ Reports
```

🛑 每个 task 验证 task 内**每对相邻页面的三端一致性**（源页 push → route 定义 → 目标页读取）。至少 2 个 scenario 覆盖 2 对跳转。
🛑 **每个 task 至少 1 个 error scenario**：passBy 不匹配（源页用 query 但契约要求 params）或参数名不一致（源页传 `orderId` 目标页取 `id`）。
🛑 **targetFiles = 源页（跳转起点）+ 所有相邻目标页**。不包含 router/index.js（路由注册由 integ 层保证）。缺源页会导致 C 步"白名单限制"无法修复导航入口。

### navigation scenario 类型

| category | 验证内容 | 测试方式 |
|----------|---------|---------|
| correct | 源页含目标路由名 + passBy 匹配 + 参数名一致 + 返回导航 | 静态 `fs.readFileSync` + `toContain` |
| error | passBy 不匹配（query↔params 冲突）或参数名不一致 | 同上 |
| auth-flow | 🆕 登录后 role 跳转 + store 数据消费 | 静态 `fs.readFileSync` + `jest.mock` store |

🛑 **auth-flow 场景必须包含 `loginPage` 和 `storeFile`**，targetFiles 必须同时含 store 和登录页。
🛑 **auth-flow 硬约束**：检查 store 源码不出现 `res.data.data`（request.js 拦截器已剥 wrapper）。

```json
{
  "id": "t_nav_auth_flow",
  "layer": "navigation",
  "testType": "interface",
  "sourceTask": "f_auth_pages",
  "targetFiles": [
    "src/pages/auth/login.vue", "src/pages/auth/register.vue",
    "src/pages/auth/reset-password.vue", "src/pages/index.vue",
    "src/stores/user.js"],
  "dependencies": ["t_frontend_auth_pages", "t_frontend_home", "t_infra_stores"],
  "testFramework": "jest",
  "description": "验证登录↔注册↔重置密码↔首页 相邻页面间的 passBy 和参数传递，以及登录后角色跳转 store 数据链",
  "note": "🛑 相邻页面 A↔B 在同一 task，防止循环依赖",
  "testScenarios": [
    {
      "scenario": "Login → Home — query 传递 redirect",
      "category": "correct",
      "input":  {"from": "Login.vue", "push": "router.push({name:'Home', query:{redirect:'/cart'}})", "passBy": "query", "param": "redirect"},
      "output": {"route": "path:'/' 无动态段", "to": "Home.vue", "read": "route.query.redirect"}
    },
    {
      "scenario": "Login → Register — 无参数传递",
      "category": "correct",
      "input":  {"from": "Login.vue", "push": "router.push({name:'Register'})", "passBy": "none"},
      "output": {"route": "path:'/auth/register' 无动态段", "to": "Register.vue", "read": "无 params/query 读取"}
    },
    {
      "scenario": "Login 成功后 role=user 跳转首页 — store 消费 API 返回值 + router.push('/')",
      "category": "auth-flow",
      "input":  {"loginPage": "src/pages/auth/login.vue", "storeFile": "src/stores/user.js"},
      "output": {"check": "res.data.data 禁止出现", "roleCheck": "user.role（非顶层 role）", "redirect": "router.push('/')"}
    },
    {
      "scenario": "Login 成功后 role=merchant 跳转商家后台",
      "category": "auth-flow",
      "input":  {"loginPage": "src/pages/auth/login.vue", "storeFile": "src/stores/user.js"},
      "output": {"roleCheck": "user.role === 'merchant' → {name:'MerchantDashboard'}"}
    },
    {
      "scenario": "Login 成功后 role=admin 跳转平台后台",
      "category": "auth-flow",
      "input":  {"loginPage": "src/pages/auth/login.vue", "storeFile": "src/stores/user.js"},
      "output": {"roleCheck": "user.role === 'admin' → {name:'AdminDashboard'}"}
    },
    {
      "scenario": "Register 传参错 — params 替代 query",
      "category": "error",
      "input":  {"from": "Register.vue", "push": "router.push({name:'Home', params:{redirect:'/cart'}})", "passBy": "params"},
      "output": {"to": "Home.vue", "read": "route.query.redirect", "expect": "undefined（passBy 不匹配）"}
    }
  ]
}
```

🛑 navigation 每个 task 覆盖一组相邻页面，每对相邻页面 1 个 correct scenario。A↔B 双向放在同一 task。targetFiles 含 router + 全部涉及页面。

---

## 🛑 输出格式铁律

**JSON 文件只包含 tasks 数组。禁止附带任何元数据**：

- ✅ 正确: `[{"id": "t_api_auth", ...}, {"id": "t_dbapi_auth", ...}]`
- ❌ 错误: `{"tasks": [...], "counts": {...}, "_meta": {...}}`

禁止输出的字段: `counts`, `_meta`, `closures`, `rules_applied`, `contract_refs`, `total_scenarios`, `category_distribution`。这些都是 Agent 自检信息，不是测试任务数据。

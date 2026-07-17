# 接口层 — api + db-api + navigation 契约（Step 2 · 自下而上第2层）

## 角色
基于 plan_tree（§2 节点表 + §4 页面导航）+ data 契约（具体表名/字段名），生成 api + db-api + navigation 契约。
🛑 这是自下而上第二层——只依赖 data 契约的字段名。api 端点从 plan_tree §2 节点表推导。

## api — HTTP 接口

```json
{
  "type": "api",
  "contractId": "api_order",
  "apiGroup": "order",
  "basePath": "/api/orders",
  "endpoints": [{
    "method": "POST",
    "path": "/",
    "frontendFunction": "createOrder",
    "auth": true,
    "roles": ["buyer"],
    "middlewareChain": ["authenticate", "hasRole('buyer')"],
    "description": "创建订单",
    "request": {
      "note": "addressId来自地址选择结果，cartItemIds来自购物车勾选项",
      "fields": [
        {"name": "addressId", "type": "int", "required": true, "validation": {"type": "int", "min": 1}, "note": "收货地址ID，来自用户地址管理"},
        {"name": "cartItemIds", "type": "array<int>", "required": true, "validation": {"type": "array", "minItems": 1}, "note": "购物车已勾选的商品项ID列表"}
      ],
      "example": {"addressId": 1, "cartItemIds": [10,11]}
    },
    "response": {
      "status": 200,
      "note": "返回订单信息供前端跳转支付页（需要orderId拼支付URL）",
      "fields": [
        {"name": "orderId", "type": "int", "note": "订单自增ID，后续支付/退款/查询用"},
        {"name": "orderNo", "type": "string", "note": "雪花算法生成的订单号，展示给用户"},
        {"name": "status", "type": "string", "value": "pending_pay", "note": "初始状态，前端据此决定展示'去支付'按钮"}
      ],
      "example": {"success": true, "data": {"orderId": 100, "orderNo": "SN20260101", "status": "pending_pay"}}
    },
    "errors": [
      {"code": "CART_EMPTY", "httpStatus": 400, "message": "购物车为空"},
      {"code": "INSUFFICIENT_STOCK", "httpStatus": 422, "message": "库存不足"}
    ],
    "pagination": null
  }],
  "frontendApiModule": "src/api/order.js",
  "backendRouteFile": "routes/order.js",
  "nfr": {}
}
```

🛑 `request.fields[].name` 和 `response.fields[].name` 必须 camelCase。
🛑 禁止用 typeHints.note 字符串代替结构化 fields。
🛑 **api note 铁律**: `request.note`（数据从哪里来）、`response.note`（数据给谁用）、`request.fields[].note`（每个字段的来源/含义）、`response.fields[].note`（每个字段的用途）——全部必填。
🛑 **example + errors 铁律**: 每个 endpoint 必须有 `request.example`（具体 JSON 示例）+ `errors[]`（≥2个，至少覆盖缺必填字段+认证失败）。
🛑 🆕 `frontendFunction`: 前端 `src/api/*.js` 中调用此端点的导出函数名。必须与前端API模块的 `export function` 名称完全一致。
🛑 🆕 `middlewareChain`: 路由挂载的中间件**顺序**。Agent按此顺序挂载: `router.{method}(path, authenticate, hasRole('admin'), controller)`。
🛑 🆕 `fields[].validation`: 校验规则直接转译为代码。`{"type":"int","min":1}` → `if (!Number.isInteger(v) || v<1) throw...`
🛑 🆕 `pagination`: 列表端点必须声明。`{"pageParam":"page","sizeParam":"pageSize","defaultSize":20}` 或 `null`（非列表端点）。
🛑 🆕 `nfr` 可选字段: `rateLimit`(限流窗口+最大次数), `xss`(输出编码)

## db-api — 数据库操作

```json
{
  "type": "db-api",
  "contractId": "db_api_create_order",
  "operation": "CRUD_CREATE",
  "tableName": "orders",
  "description": "创建订单记录",
  "input": {
    "where": [],
    "values": [
      {"column": "user_id", "type": "int", "required": true, "note": "买家ID，来自auth_token"},
      {"column": "order_no", "type": "varchar(32)", "required": true, "note": "雪花算法订单号"},
      {"column": "total_amount", "type": "decimal(10,2)", "required": true, "note": "订单总金额"},
      {"column": "status", "type": "varchar(20)", "required": true, "note": "初始状态pending_pay"}
    ],
    "set": [],
    "note": "user_id来自auth_token，order_no由snowflake生成"
  },
  "output": {
    "columns": ["id","order_no","status"],
    "returnType": "insertId",
    "note": "返回自增ID和订单号供后续支付使用",
    "nullable": false
  },
  "implicitConditions": [],
  "usesTransaction": true,
  "nfr": {}
}
```

🛑 **input 拆分规则（铁律）**:
  - CRUD_CREATE: 只填 `values[]`（INSERT 的列），`where`和`set`为空数组
  - CRUD_READ: 只填 `where[]`（SELECT 的 WHERE 条件列），`values`和`set`为空
  - CRUD_UPDATE: 填 `set[]`（UPDATE SET 列）+ `where[]`（WHERE 条件列），`values`为空
  - CRUD_DELETE: 只填 `where[]`
  - 每个列条目包含 `column`(列名) + `type`(类型) + `required`(是否必填) + `note`(来源含义)
🛑 `output.returnType`: `"rows"`(返回数组) | `"insertId"`(返回自增ID) | `"affectedRows"`(返回影响行数) | `"none"`
🛑 `implicitConditions`: 软删除/多租户等自动附加的WHERE条件。例: `[{"column":"deleted_at","operator":"IS NULL","note":"软删除过滤"}]`
🛑 `arrayExpand`: 当WHERE列是数组时标记。例: `{"column":"id","expandTo":"IN"}` → Agent生成 `WHERE id IN (?,?,?)` 而非 `WHERE id IN (:ids)`
🛑 `input.columns`/`output.columns` 的列名必须与 model 契约的 `fields[].name` 完全一致。
🛑 `input.note` / `output.note` 描述数据的来源和去向——帮助工程师理解上下文。
🛑 禁止使用 `typeHints.note` / `sqlTemplate` / `params` / `returns` 字段——已废弃。
🛑 `nfr` 可选字段: `sqlInjection`(参数化), `concurrency.lockHint`(FOR_UPDATE/NOWAIT), `performance.expectIndexUsage`(期望使用的索引)

## navigation — 页面跳转

```json
{
  "type": "navigation",
  "contractId": "nav_order_to_payment",
  "fromPage": "Order",
  "toPage": "Payment",
  "fromPageFile": "src/pages/frontend/order/Order.vue",
  "toPageFile": "src/pages/frontend/order/Payment.vue",
  "toPageRoute": "/payment/:orderId",
  "toPageRouteName": "Payment",
  "passBy": "params",
  "params": [{"name": "orderId", "type": "int", "required": true}],
  "trigger": {
    "event": "submit_success",
    "element": "提交订单按钮",
    "code": "router.push({name:'Payment', params:{orderId: res.data.orderId}})"
  },
  "targetRead": {
    "source": "route.params",
    "code": "const orderId = route.params.orderId"
  },
  "guardRedirect": null,
  "auth": true,
  "note": "下单成功后跳转到支付页，携带orderId用于查询订单信息和发起支付"
}
```

🛑 `passBy=params` 时 `toPageRoute` 必须含 `:paramName` 动态段。
🛑 `params` 数组每项含 `name` + `type` + `required`，不只是名称列表。
🛑 `note` 必填——说明跳转的业务场景。
🛑 🆕 `trigger`: 源页面**如何触发**跳转。`event`(触发时机: click/submit_success/beforeEach_guard), `code`(跳转代码模板,直接嵌入源页面)。
🛑 🆕 `targetRead`: 目标页面**如何读取**参数。`source`(数据来源: route.params/route.query), `code`(读取代码,直接嵌入目标页面)。
🛑 🆕 `guardRedirect`: 路由守卫重定向。`{"condition":"!token","action":"redirect('/auth/login', {query:{redirect}})"}` 或 `null`。

## 生成规则

- api: plan_tree §2 每个有能力的模块→1个api契约。从 business 契约 logic.apiMapping 反推需要哪些端点。
- db-api: 遍历 business 契约 logic.dbApiMapping 引用→每个引用生成1个db-api。从 logic.process 提取 operation+tableName。
- navigation: plan_tree §4 页面导航表，每对相邻页面→1个navigation。
- 🛑 **同一对页面只生成一个 navigation 契约**。A→B 和 B→A 是同一对，不要生成两个。fromPage/toPage 选谁作为起点不影响——测试层的 navigation task 会将双向放在同一个 task 中。
- 🛑 db-api 列名必须与 data 契约 model.fields[].name **原样一致**——从 data 契约复制
- 🛑 格式: `{"contracts": [...]}` 平铺数组，不做二级嵌套

---

## 执行指令

### 任务
接口层契约生成（自下而上第2层）。基于 plan_tree + data 契约，生成 api + db-api + navigation。
🛑 **按类型拆成 3 次 create_file 调用**，每次生成一种类型。不要一次性输出全部。

### 生成前参数提取（强制步骤）
在调用 create_file 之前，必须先输出:

```
从 plan_tree §2 节点表推导 api:
  每个节点的 api候选列 → api 端点
  api候选去重后共 ? 个 → api 契约 ? 个

从 plan_tree §2 节点表推导 db-api:
  每个节点的数据库操作 → db-api
  DB操作去重后共 ? 个 → db-api 契约 ? 个

从 plan_tree §4 推导:
  页面相邻对共 ? 对 → navigation 契约 ? 个

api 清单:
  api_? (basePath=?, 端点: ?) — 来自 plan_tree §2 节点?
  ...（共 ? 个）

db-api 清单:
  db_api_? (operation=?, tableName=?) — 来自 plan_tree §2 节点? DB操作
  ...（共 ? 个）

navigation 清单:
  nav_? (?→?, passBy=?)
  ...（共 ? 个）

总计: ? api + ? db-api + ? navigation = ? 个契约
```

### 写入策略（写前自检 → 一次写对）

🛑 **写前自检（在每次 create_file 之前，先对照参数提取表确认数量和引用正确）**：
1. 对照参数提取表确认 api 数量 = 预估数 → self-check ✅ → create_file
2. 对照参数提取表确认 db-api 数量 = 预估数 → self-check ✅ → create_file  
3. 对照参数提取表确认 navigation 数量 = 预估数 → self-check ✅ → create_file

🛑 **不要在写入后才检查**——create_file 返回后再发现问题只能 edit_batch 修，浪费迭代次数。写前自检可避免此问题。

- 🛑 第1次 create_file: 写前自检通过 → 写入 **api 契约** → `_contracts_interfaces_api.json`
- 🛑 第2次 create_file: 写前自检通过 → 写入 **db-api 契约** → `_contracts_interfaces_dbapi.json`
- 🛑 第3次 create_file: 写前自检通过 → 写入 **navigation 契约** → `_contracts_interfaces_nav.json`
- 🛑 全部完成 → 输出 `[接口层契约完成]`

### 铁律
- 🛑 **引用铁律**: db-api 的 tableName/columns 必须与 data 契约 model.fields[].name 完全一致——从 data 契约原样复制
- 🛑 api 端点从 plan_tree §2 节点表的 api候选列推导
- 🛑 db-api 从 plan_tree §2 节点表的数据库操作推导
- 🛑 navigation 从 plan_tree §4 页面导航表提取相邻页面配对
- 🛑 **数量约束**: db-api数 = 所有节点的数据库操作数(去重), navigation数 = plan_tree页面相邻对数
- 🛑 **禁止嵌套**: 不要在 contracts 数组里出现 `{"navigations":[...]}` 等二级包裹
- 🛑 db-api: input 拆分为 where/values/set(按CRUD类型), implicitConditions(软删除), arrayExpand(IN展开), output.returnType
- 🛑 api: endpoints[].frontendFunction(前端导出名), endpoints[].middlewareChain(中间件顺序), fields[].validation(校验规则)
- 🛑 navigation: trigger(跳转代码模板), targetRead(参数读取代码)

### 禁止行为
- 禁止一次性输出全部 3 种类型（超长 JSON 必然出错）
- 禁止写摘要 md
- 禁止跳过参数提取表直接写 JSON
- 禁止 contracts 数组中出现二级包裹

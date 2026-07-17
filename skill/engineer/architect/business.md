# 业务层 — scenario + logic 契约（Step 3 · 自下而上第3层）

## 角色
基于 plan_tree（§2 业务流程图 + §1 模块清单）+ data 契约（具体表名）+ interfaces 契约（api 端点），生成 scenario（多业务联合）和 logic（单业务逻辑）契约。
🛑 这是自下而上第三层——引用 data 契约的 tableName 和 interfaces 契约的 api.contractId。

---

## 执行指令

### 任务
遍历 plan_tree §2 的每个节点，**逐节点生成 logic**；遍历 §2 的每条链路，**逐链路生成 scenario**。两种类型必须同时生成，缺一不可。

### 从 plan_tree 节点推导 logic（对照表）

🛑 plan_tree §2 业务流程图每一行是一个节点。按此表逐列映射:

| plan_tree 节点列 | logic 字段 | 怎么填 |
|-----------------|-----------|--------|
| 动作 | `description` | 原样抄 |
| logic候选 | `contractId` | `logic_{候选名}` |
| api候选 | `apiMapping` | 去 interfaces 契约找对应的 `api.contractId` |
| 输入(字段+来源) | `input` | 每个字段 → `input.{name}`，来源 → `from` |
| 输出(字段+去向) | `output` | 每个字段 → `output.{name}`，去向 → `note` |
| 校验规则 | `input.{name}.validation` | 直接转译 |
| 事务边界 | `transactionBoundary` | 有 BEGIN/COMMIT → true，否则 false |
| 错误码→Agent动作 | `errorMapping` | 错误码 + httpStatus + message |
| 基础设施(Redis/MQ等) | `process`步骤 + `nfr` | 有 Redis → process 中描述操作 |

### 生成前参数提取（强制步骤）

在调用 create_file 之前，**必须先逐节点列出所有 logic**:

```
plan_tree §2 流程节点共 ? 个:
  节点1: {动作} → logic_{候选名} (apiMapping=[api_?], dbApiMapping=[db_api_?])
  节点2: {动作} → logic_{候选名} (apiMapping=[api_?], dbApiMapping=[db_api_?])
  ...（逐节点列出，共 ? 个 logic）

plan_tree §2 业务链路共 ? 条:
  scenario_? (链路: ?→?→?, 共?步, logicRef=[logic_?, ...])
  ...（共 ? 个 scenario）

总计: ? scenario + ? logic = ? 个契约
🛑 确认: logic 数量 > 0 ✅  scenario 数量 > 0 ✅
```

🛑 **logic 不一定要多层事务**。简单的查库/校验/发验证码 3~4 步即可（参考下方「短示例」）。

### 铁律
- 🛑 **一一对应**: 每个节点 → 1 个 logic，每条链路 → 1 个 scenario。禁止跳过任何节点。
- 🛑 **引用原样**: apiMapping 从 interfaces 契约复制 api.contractId，dbApiMapping 从 data 契约复制 tableName。
- 🛑 **格式**: `{"contracts": [所有scenario..., 所有logic...]}` 全部平铺在一个数组里。
- 🛑 **必填字段**: logic 必须包含 serviceSignature / input.validation / process[].postCondition / idempotency / nfr
- 🛑 **必填字段**: scenario 每个 chain step 必须包含 handoff(mechanism + typeMatches)

### 写入策略（最多3次）
- 第1次: 输出参数提取表（逐节点列出 logic）→ create_file → scenario + logic 同时写入
- 第2次: 对照 plan_tree §2 逐节点检查 logic 覆盖，有遗漏则补全
- 第3次: 确认 scenario数=链路数 **且 logic数=节点数** → 输出 `[业务层契约完成]`

### 禁止行为
- **🛑 禁止只生成 scenario 不生成 logic，或反之。**
- 禁止拆成多个文件（只有一个 `_contracts_business.json`）
- 禁止跳过参数提取表直接写 JSON

### 产物
🛑 唯一产物由动态上下文中的文件路径指定。用 `create_file` 写入。
🛑 完成后输出 `[业务层契约完成]`。

---

## logic 参考规范

### 必填字段速查

| 字段 | 必须 | 说明 |
|------|:---:|------|
| `type` | ✅ | 固定 `"logic"` |
| `contractId` | ✅ | `logic_{名称}` |
| `description` | ✅ | 处理链一句话描述 |
| `serviceSignature` | ✅ | 函数名 + 文件路径 + 参数列表 + 返回类型 |
| `input` | ✅ | 每个字段含 type / from / validation / note |
| `output` | ✅ | 每个字段含 type / note / value(初始值) |
| `process` | ✅ | 步骤链，每步含 step / action / postCondition / note |
| `errorMapping` | ✅ | ≥1 个错误码 |
| `apiMapping` | ✅ | 引用 interfaces 的 api.contractId |
| `dbApiMapping` | ✅ | 引用 data 的 model.tableName |
| `transactionBoundary` | ✅ | 有事务 → true |
| `rollback` | 条件 | 有事务时必填 |
| `idempotency` | 条件 | 写操作时必填: keyField + strategy |
| `nfr` | ✅ | ≥1 条非功能约束 |
| `authentication` | ✅ | `"required"` / `"optional"` |
| `roles` | ✅ | 允许的角色列表 |

### serviceSignature

```json
"serviceSignature": {
  "functionName": "createOrder",
  "file": "services/orderService.js",
  "params": [{"name": "userId", "type": "int", "required": true}],
  "returns": {"type": "object", "fields": ["orderId", "orderNo"]}
}
```

### input.{field}.validation 转译规则

| validation | 转译成的代码 |
|-----------|------------|
| `required: true` | `if (!field) throw Error('MISSING_XXX')` |
| `min: N` / `max: N` | `if (field < N) throw...` |
| `pattern: "regex"` | `if (!/regex/.test(field)) throw...` |
| `minLength: N` / `maxLength: N` | `if (field.length < N) throw...` |
| `mustExist: {table, column}` | `SELECT 1 FROM t WHERE col=?` → 不存在则抛 |
| `errorCode: "XXX"` | `throw new Error('XXX')` |

### process[].postCondition

```json
{"step": 4, "postCondition": {"check": "affectedRows > 0", "onFail": {"throw": "CONCURRENCY_CONFLICT", "status": 409}}}
```
🛑 每步的 postCondition 转译为代码中的断言/错误检查。

### idempotency

```json
"idempotency": {"keyField": "orderNo", "strategy": "INSERT_IGNORE", "note": "去重"}
```
策略: `INSERT_IGNORE` / `SELECT_BEFORE_INSERT` / `UNIQUE_CONSTRAINT`

### nfr

```json
"nfr": {"concurrency": {"strategy": "pessimistic_lock"}, "audit": {"logAction": "create_order"}}
```
🛑 `"pessimistic_lock"` → `SELECT ... FOR UPDATE`

---

### 完整示例：复杂事务型（logic_create_order）

```json
{
  "type": "logic",
  "contractId": "logic_create_order",
  "description": "创建订单: 校验→事务→锁库存→INSERT→COMMIT",
  "authentication": "required",
  "roles": ["buyer"],
  "transactionBoundary": true,
  "serviceSignature": {
    "functionName": "createOrder",
    "file": "services/orderService.js",
    "params": [
      {"name": "userId", "type": "int", "required": true},
      {"name": "addressId", "type": "int", "required": true},
      {"name": "cartItemIds", "type": "array<int>", "required": true}
    ],
    "returns": {"type": "object", "fields": ["orderId", "orderNo", "totalAmount", "status"]}
  },
  "input": {
    "userId": {"type": "int", "from": "auth_token", "validation": {"required": true, "min": 1}, "note": "当前登录用户ID"},
    "addressId": {"type": "int", "validation": {"required": true, "min": 1}, "note": "收货地址ID"},
    "cartItemIds": {"type": "array<int>", "validation": {"required": true, "minItems": 1, "maxItems": 50}, "note": "购物车勾选项ID列表"}
  },
  "output": {
    "orderId": {"type": "int", "note": "订单自增ID，前端跳转支付页用"},
    "orderNo": {"type": "string", "note": "雪花算法订单号，支付回调幂等键"},
    "status": {"type": "string", "value": "pending_pay", "note": "初始状态"}
  },
  "process": [
    {"step": 1, "action": "校验购物车非空", "postCondition": {"check": "cartItemIds.length > 0", "onFail": {"throw": "CART_EMPTY", "status": 400}}, "note": "为空throw CART_EMPTY"},
    {"step": 2, "action": "BEGIN TRANSACTION", "note": "扣库存+建订单+清购物车原子执行"},
    {"step": 3, "action": "SELECT stock FOR UPDATE", "postCondition": {"dbState": {"table": "products", "expect": "rows.length === cartItemIds.length"}}, "note": "悲观行锁"},
    {"step": 4, "action": "UPDATE stock=stock-qty WHERE stock>=qty", "postCondition": {"check": "affectedRows > 0", "onFail": {"throw": "CONCURRENCY_CONFLICT", "status": 409}}, "note": "affectedRows=0→并发冲突"},
    {"step": 5, "action": "INSERT orders + order_items", "note": "order_items含sku_snapshot快照"},
    {"step": 6, "action": "DELETE FROM carts WHERE user_id=? AND sku_id IN (?)", "note": "清空已下单购物车项"},
    {"step": 7, "action": "COMMIT", "note": "失败则ROLLBACK全部"}
  ],
  "rollback": "任一步失败→ROLLBACK, stock恢复, 购物车恢复",
  "errorMapping": {
    "CART_EMPTY": {"httpStatus": 400, "message": "购物车为空"},
    "INSUFFICIENT_STOCK": {"httpStatus": 422, "message": "库存不足"},
    "CONCURRENCY_CONFLICT": {"httpStatus": 409, "message": "并发冲突请重试"}
  },
  "apiMapping": ["api_order"],
  "dbApiMapping": ["db_api_create_order", "db_api_lock_inventory", "db_api_clear_cart"],
  "idempotency": {"keyField": "orderNo", "strategy": "INSERT_IGNORE", "note": "雪花算法orderNo去重"},
  "nfr": {"concurrency": {"strategy": "pessimistic_lock"}, "audit": {"logAction": "create_order", "logUserId": true}}
}
```

### 短示例：简单查询型（logic_login — 无事务，4步）

```json
{
  "type": "logic",
  "contractId": "logic_login",
  "description": "用户登录: 校验手机号→查用户→验密码→生成JWT",
  "authentication": "optional",
  "roles": [],
  "transactionBoundary": false,
  "serviceSignature": {
    "functionName": "loginByPhone",
    "file": "services/authService.js",
    "params": [{"name": "phone", "type": "string", "required": true}, {"name": "password", "type": "string", "required": true}],
    "returns": {"type": "object", "fields": ["token", "refreshToken", "user"]}
  },
  "input": {
    "phone": {"type": "string", "from": "req.body", "validation": {"required": true, "pattern": "^1[3-9]\\d{9}$"}},
    "password": {"type": "string", "from": "req.body", "validation": {"required": true, "minLength": 6}}
  },
  "output": {
    "token": {"type": "string", "note": "JWT access token，前端内存存储"},
    "refreshToken": {"type": "string", "note": "refresh token，HttpOnly Cookie"},
    "user": {"type": "object", "note": "{userId, phone, nickname, avatar, role}"}
  },
  "process": [
    {"step": 1, "action": "校验手机号格式", "postCondition": {"check": "/^1[3-9]\\d{9}$/.test(phone)", "onFail": {"throw": "INVALID_PHONE", "status": 400}}},
    {"step": 2, "action": "SELECT * FROM users WHERE phone=?", "postCondition": {"check": "row !== null", "onFail": {"throw": "PHONE_NOT_FOUND", "status": 404}}},
    {"step": 3, "action": "bcrypt.compare(password, row.password_hash)", "postCondition": {"check": "match === true", "onFail": {"throw": "PASSWORD_WRONG", "status": 401}}},
    {"step": 4, "action": "jwt.sign + INSERT INTO login_logs", "note": "生成token并记录登录日志"}
  ],
  "errorMapping": {
    "INVALID_PHONE": {"httpStatus": 400, "message": "手机号格式不正确"},
    "PHONE_NOT_FOUND": {"httpStatus": 404, "message": "手机号未注册"},
    "PASSWORD_WRONG": {"httpStatus": 401, "message": "密码错误"}
  },
  "apiMapping": ["api_auth"],
  "dbApiMapping": ["db_api_find_user_by_phone"],
  "idempotency": null,
  "nfr": {"rateLimit": {"window": "1m", "max": 5}, "audit": {"logAction": "login", "logUserId": true}}
}
```

---

## scenario 参考规范

### 必填字段速查

| 字段 | 必须 | 说明 |
|------|:---:|------|
| `type` | ✅ | 固定 `"scenario"` |
| `contractId` | ✅ | `scenario_{名称}` |
| `description` | ✅ | 链路一句话描述 |
| `priority` | ✅ | `"main_trunk"` |
| `chain` | ✅ | 步骤数组 |
| `chain[].step` | ✅ | 步骤序号 |
| `chain[].logicRef` | ✅ | 引用 logic.contractId |
| `chain[].taskRef` | ✅ | 引用 backend taskId |
| `chain[].consumes` | ✅ | 从前一步拿什么数据（字段级展开） |
| `chain[].produces` | ✅ | 给下一步提供什么数据（字段级展开） |
| `chain[].handoff` | ✅ | 交接声明: to / mechanism / typeMatches |
| `chain[].note` | ✅ | 格式: `[场景] 位置。[输入] 来源。[输出] 去向。` |
| `finalState` | ✅ | 链路终态描述 |

### S4 闭合铁律 — 共享字段传递

- 起始步骤(step 1)的 produces 包含 `userId`, `token`, `role`
- 每个后续 step 的 produces = 自己新字段 ∪ 前一步的共享字段(userId/token/role)
- 结果: 任何一步都可以从 produces 拿到认证信息，S4 自然闭合
- 🛑 produces/consumes 禁止裸 `"array"`/`"object"`，必须展开到字段级

### handoff 规范

```json
"handoff": {
  "to": "step3",
  "mechanism": "http_response",
  "typeMatches": [{"field": "orderId", "fromType": "int", "toType": "int", "mustMatch": true}],
  "note": "orderId通过API响应返回前端"
}
```
`mechanism` 取值: `http_response` / `jwt_payload` / `db_query` / `route_params`

### 完整示例

```json
{
  "type": "scenario",
  "contractId": "scenario_buyer_checkout",
  "priority": "main_trunk",
  "description": "买家从登录到支付的完整交易链路",
  "chain": [
    {"step": 1, "logicRef": "logic_login", "taskRef": "b_auth",
     "consumes": {},
     "produces": {"userId": "int", "token": "string", "role": "string"},
     "handoff": {"to": "step2", "mechanism": "jwt_payload", "note": "userId+role编码在JWT中"},
     "note": "[场景] 用户身份认证。[输出] userId+token+role→后续共享"},
    {"step": 2, "logicRef": "logic_create_order", "taskRef": "b_order",
     "consumes": {"userId": {"type": "int", "from": "step1.produces", "via": "req.userId"}, "cartItemIds": {"type": "array<int>", "from": "frontend_input", "via": "req.body"}, "addressId": {"type": "int", "from": "frontend_input", "via": "req.body"}},
     "produces": {"userId": "int", "token": "string", "orderId": "int", "orderNo": "string", "totalAmount": "decimal", "status": "pending_pay"},
     "handoff": {"to": "step3", "typeMatches": [{"field": "orderId", "fromType": "int", "toType": "int", "mustMatch": true}], "mechanism": "http_response", "note": "orderId通过API响应返回"},
     "note": "[场景] 创建订单。[输入] userId+token继承, cartItemIds来自购物车。[输出] orderId+orderNo→下一步支付"}
  ],
  "finalState": "订单已创建，库存已扣减，等待支付"
}
```

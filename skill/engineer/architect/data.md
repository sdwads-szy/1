# 数据层 — model + auth 契约（Step 1 · 自下而上第1层）

## 角色
基于 plan_tree 的数据实体地图（§3）+ 鉴权需求（§5），生成 model（数据库表）和 auth（认证）契约。
🛑 这是自下而上的第一层——无契约依赖。所有字段信息来自 plan_tree §3。

## model — 数据库表

```json
{
  "type": "model",
  "contractId": "model_order",
  "tableName": "orders",
  "description": "订单核心表：记录每笔交易的金额、状态、关联买家商家",
  "fields": [
    {"name": "id", "type": "int", "primary": true, "autoIncrement": true, "comment": "自增主键"},
    {"name": "order_no", "type": "varchar(32)", "nullable": false, "unique": true, "comment": "雪花算法生成的订单号，全局唯一"},
    {"name": "user_id", "type": "int", "nullable": false, "comment": "买家ID，关联users表"},
    {"name": "status", "type": "enum('pending_pay','paid','shipped','received','cancelled')", "default": "pending_pay", "comment": "订单状态，严格控制流转"},
    {"name": "total_amount", "type": "decimal(10,2)", "nullable": false, "comment": "订单总金额（未优惠）"},
    {"name": "created_at", "type": "timestamp", "default": "CURRENT_TIMESTAMP", "comment": "记录创建时间，自动生成"}
  ],
  "indexes": [{"name": "idx_user_status", "columns": ["user_id","status"]}],
  "foreignKeys": [{"column": "user_id", "refTable": "users", "refColumn": "id"}],
  "stateMachine": {
    "field": "status",
    "transitions": [
      "pending_pay→paid", "paid→shipped", "shipped→received",
      "pending_pay→cancelled"
    ]
  }
}
```

🛑 字段约束:
- `type` 必须含长度: `varchar(128)`, `decimal(10,2)`
- 金额用 `decimal(10,2)`，禁止 `float`/`double`
- 含 `status` 字段的表必须有 `stateMachine`
- FK 必须写在 `foreignKeys` 数组里，不写注释里
🛑 **model description + comment 铁律**:
- 每个 model 必须有 `description`——一句话说清这张表在业务中的角色
- 每个 `fields[].comment` 必填——说明字段的业务含义，不能只靠字段名

## auth — 认证

```json
{
  "type": "auth",
  "contractId": "auth_bearer",
  "description": "全站JWT Bearer认证方案: access token(2h)+refresh token(7d)双token机制，HttpOnly Cookie保存refresh token",
  "tokenConfig": {
    "accessTokenExpiry": 7200,
    "refreshTokenExpiry": 604800,
    "algorithm": "HS256",
    "payloadFields": ["userId","role","iat","exp"],
    "secretEnvVar": "JWT_SECRET"
  },
  "loginEndpoint": {
    "path": "/api/auth/login",
    "method": "POST",
    "description": "手机号+密码登录",
    "request": {
      "fields": [
        {"name": "phone", "type": "string", "required": true, "validation": {"pattern": "^1[3-9]\\d{9}$"}, "note": "11位手机号"},
        {"name": "password", "type": "string", "required": true, "validation": {"minLength": 6}, "note": "密码，至少6位"}
      ],
      "example": {"phone": "13800138000", "password": "Abc12345"}
    },
    "response": {
      "fields": [
        {"name": "token", "type": "string", "note": "access token，前端内存存储"},
        {"name": "refreshToken", "type": "string", "note": "refresh token，HttpOnly Cookie"},
        {"name": "user", "type": "object", "note": "{userId, phone, nickname, avatar, role}"}
      ]
    }
  },
  "registerEndpoint": {
    "path": "/api/auth/register",
    "method": "POST",
    "description": "手机号注册",
    "request": {
      "fields": [
        {"name": "phone", "type": "string", "required": true, "validation": {"pattern": "^1[3-9]\\d{9}$"}},
        {"name": "code", "type": "string", "required": true, "validation": {"minLength": 6, "maxLength": 6}},
        {"name": "password", "type": "string", "required": true, "validation": {"minLength": 8, "mustContain": ["digit","letter"]}}
      ]
    }
  },
  "refreshEndpoint": {
    "path": "/api/auth/refresh",
    "method": "POST",
    "description": "用refreshToken换取新access token",
    "request": {"fields": [{"name": "refreshToken", "type": "string", "required": true, "source": "cookie"}]},
    "response": {"fields": [{"name": "token", "type": "string"}]}
  },
  "errorMapping": {
    "TOKEN_MISSING": {"httpStatus": 401, "message": "未提供认证令牌，请先登录"},
    "TOKEN_EXPIRED": {"httpStatus": 401, "message": "令牌已过期"},
    "TOKEN_INVALID": {"httpStatus": 401, "message": "令牌无效"},
    "PHONE_NOT_FOUND": {"httpStatus": 404, "message": "手机号未注册"},
    "PASSWORD_WRONG": {"httpStatus": 401, "message": "密码错误"},
    "PHONE_EXISTS": {"httpStatus": 409, "message": "手机号已注册"},
    "WEAK_PASSWORD": {"httpStatus": 422, "message": "密码强度不足，至少8位含数字和字母"},
    "INVALID_CODE": {"httpStatus": 400, "message": "验证码无效"},
    "CODE_EXPIRED": {"httpStatus": 400, "message": "验证码已过期"}
  },
  "frontendContract": {
    "storageKeys": {"token": "auth_token", "refreshToken": "refresh_token"},
    "requestHeader": "Authorization",
    "headerFormat": "Bearer {token}"
  },
  "middlewareContract": {
    "middlewareFile": "middleware/auth.js",
    "exports": ["authenticate","optionalAuth"],
    "reqInjection": {"req.userId": "decoded.userId", "req.user": "{userId,role}"}
  },
  "nfr": {
    "rateLimit": {"loginWindow": "1m", "loginMax": 5, "smsWindow": "1m", "smsMax": 1},
    "password": {"hashAlgo": "bcrypt", "saltRounds": 10}
  }
}
```

🛑 tokenConfig/frontendContract/middlewareContract 三项缺一不可。
🛑 🆕 `loginEndpoint`/`registerEndpoint`: 定义登录/注册接口的完整契约——字段名必须与DDL列名一致。
🛑 🆕 `refreshEndpoint`: token刷新接口，前端401时调用。
🛑 🆕 `errorMapping`: 每个错误码→HTTP状态码+消息。Agent据此生成controller的catch块。
🛑 🆕 `nfr.rateLimit`: 登录限流参数。`loginWindow`+`loginMax` → express-rate-limit配置。
🛑 🆕 `nfr.password`: 密码策略。`hashAlgo`+`saltRounds` → bcrypt.hash 参数。

## 生成规则

- plan_tree §3 数据实体地图中的每个实体 → 1 个 model
- plan_tree §5 鉴权需求 → 1 个 auth
- 🛑 model 字段名/类型/约束从 plan_tree §3.2 实体摘要**原样复制**
- 🛑 model 数 ≥ plan_tree §3 实体数，对照 §7 计数表自检
- 🛑 格式: `{"contracts": [所有model..., auth]}` 全部在一个平铺数组

---

## 执行指令

### 任务
数据层契约生成（自下而上第1层）。只依赖 plan_tree 的 §3 数据实体地图 + §5 鉴权需求，无需等待其他契约。

### 生成前参数提取（强制步骤）
在调用 create_file 之前，必须先输出:

```
应生成 model 契约（对照 plan_tree §3 数据实体地图）:
  model_{entity1} (table=?) — §3 实体
  model_{entity2} (table=?) — ...
  ...（共 N 个 = plan_tree §3 实体数）

应生成 auth 契约:
  auth_bearer (1个) — §5 鉴权需求

总计: N model + 1 auth = N+1 个契约 = plan_tree §7 预估数 ✅/❌
```

### 铁律
- 🛑 model 数量铁律: model 数 ≥ plan_tree §3 实体数。少一个都不行。
- 🛑 逐个对照: plan_tree §3 每个实体 → 1 个 model。生成完后对照 §3 逐项 ✅/❌。
- 🛑 auth 必须包含: loginEndpoint(登录), registerEndpoint(注册), refreshEndpoint(刷新), errorMapping(错误码→HTTP+消息), nfr(rateLimit+password)
- 🛑 seedData 铁律: 除 carts/orders/payments 外，每张表都必须有 seedData。生成完后逐表自检（见下方 seedData 三级规则）。

### 写入策略（最多3次）
- 第1次: 输出参数提取表 → create_file → 完整文件
- 第2次: 对照 plan_tree §3 逐项检查 model 数量 + 逐表检查 seedData 覆盖（非豁免表缺 seed → 补全）
- 第3次: 确认 model 数 ≥ plan_tree §3 实体数 且 seedData 全覆盖 → 输出 `[数据层契约完成]`

### 禁止行为
- 禁止拆成 model 一个文件 auth 一个文件（只有一个 `_contracts_data.json`）
- 禁止写摘要 md
- 禁止跳过参数提取表直接写 JSON
- 禁止非豁免表缺 seedData（carts/orders/payments 以外的表必须有 seedData）

### 产物
🛑 唯一产物由动态上下文中的文件路径指定。用 `create_file` 写入。
🛑 完成后输出 `[数据层契约完成]`。

## 🆕 seedData — 种子数据（除 carts/orders/payments 外全部必填）

除 carts/orders/payments 三张动态表外，**所有 model 必须有 seedData**。在 model 契约中声明:

```json
"seedData": {
  "purpose": "3个测试用户: 买家+商家+管理员，密码统一{{bcrypt:123456}}",
  "rows": [
    {"phone": "13800000001", "password_hash": "{{bcrypt:123456}}", "nickname": "测试买家", "role": "buyer", "status": "active"},
    {"phone": "13800000002", "password_hash": "{{bcrypt:123456}}", "nickname": "测试商家", "role": "merchant", "status": "active"},
    {"phone": "13800000003", "password_hash": "{{bcrypt:123456}}", "nickname": "平台管理员", "role": "admin", "status": "active"}
  ]
}
```

🛑 `seedData.rows[]` 每条 row 的 key **必须**与 `fields[].name` 完全一致 — 列名铁律
🛑 `{{bcrypt:value}}` 是密码占位符 — seed 脚本运行时替换为真实 bcrypt 哈希
🛑 图片列（avatar/logo/icon/images/banner_image）默认用占位图路径:
  - 头像 → `/img/placeholder/avatar.svg`
  - logo/icon → `/img/placeholder/logo.svg`
  - 商品图 → `/img/placeholder/product.svg`
  - 横幅 → `/img/placeholder/banner.svg`
🛑 **种子数据判定铁律（三级规则，逐表判定）**:

### 第一级：必有种子（基础数据 — 无 FK 依赖或 FK 指向其他基础表）
这些表必须有种子数据，打开网页就能看到效果:

| 表 | 最少行数 | 说明 |
|----|:---:|------|
| users | 3 | 买家+商家+管理员各1，密码 `{{bcrypt:123456}}` |
| user_profiles | 3 | 与 users 一一对应，每个 user 1 行 |
| addresses | 3 | 每个 user 至少 1 个收货地址 |
| merchants | 2 | ≥2个已审核商家，关联 merchant 角色的 user_id |
| categories | 12 | 8顶级 + ≥4二级，树状结构 |
| logistics_companies | 3 | 顺丰/中通/圆通等常用物流商 |
| products | 20 | 覆盖全部顶级类目，价格 ¥10~¥10000，2个商家各分一半 |
| skus | 40 | 每个 product 至少 2 个 SKU（不同规格） |
| reviews | 10 | 覆盖 ≥8 个商品，≥2 个用户，评分 4~5 星 |
| review_images | 10 | 每条评价至少 1 张图 |

### 第二级：必有种子（从属数据 — FK 指向第一级基础表）
这些表本身不独立存在，但 FK 指向第一级有种子数据的表，所以可以安全添加种子:

| 表 | 最少行数 | FK 指向 | 说明 |
|----|:---:|------|------|
| audit_log | 3 | merchants | 商家入驻审核记录 |
| review_replies | 3 | reviews + users | 商家对评价的回复 |
| security_logs | 5 | users | 登录/IP记录 |

### 第三级：不加种子（运行时动态创建）
以下 3 张表的数据由用户操作动态产生，seed 了反而干扰测试:

| 表 | 原因 |
|----|------|
| **carts** | 购物车是用户实时操作。seed 的 cart 项库存过期后会变成脏数据 |
| **orders** | 订单是交易核心。seed 的订单没有真实支付回调，状态永远卡住 |
| **payments** | 支付记录必须与订单+第三方回调一致。seed 的数据无法模拟真实支付流程 |

### 🛑 铁律总结
- 不在"不加种子"列表中的表 → **必须有 seedData**（至少 1 行）
- 第一级和第二级表生成完逐表自检: `users ✅  user_profiles ✅  ...`
- 任意一张非豁免表缺 seedData → 禁止输出 `[数据层契约完成]`
- FK 指向动态表（orders/payments）的表（如 order_sub/after_sales/shipments/refund_tasks/settlements/tracking_events）：**用占位 FK 值（如 order_id=1），注明"运行时关联"**

# 测试架构师 — 逻辑层 (Step 3)

🛑 依赖推导方法见 [common.md](common.md)。
🛑 **逻辑层含 3 个子层，必须全部生成: backend_proc(~35) → logic(~10) → scenario(~10)**
🛑 **生成顺序严格遵守，每层生成完检查任务数达标后再进入下一层。**

## 场景解读

逻辑层从 `_test_plan_tree.md` 的映射表 + `_contracts_business.json` 拿到信息：

| 子层 | sourceTask | targetFiles | dependencies | scenarios 来源 |
|------|-----------|-------------|-------------|---------------|
| backend_proc | 映射表 1:1 | 只含 services | 纵向: t_api_* + t_dbapi_*；横向: 业务流程前驱（登录→下单→支付） | 每个 service 函数 1 correct + 1 error |
| logic | 契约的 process | 三件套(routes+controllers+services) | 纵向: t_backendproc_*（🛑 不依赖 t_api_*/t_dbapi_*/t_db_*） | 每个事务 1 correct + 1 error |
| scenario | 契约的 scenario chain | 涉及模块并集 | 纵向: t_logic_* + t_nav_*（🛑 logic 真理 flows[].steps[] 已聚合全部函数细节，不依赖 backend_proc/api/db_api） | 每个交接点 1 correct |

## 角色
逻辑验证专家。验证数据在业务处理中**如何变换**——输入经过处理步骤链后的输出是否与契约一致。

场景格式: **input(初始状态) + process(处理步骤链) + output(最终数据状态)**
🛑 backend_proc 用 jest，logic/scenario 用 jest+supertest

## 输出范围

按 `_test_plan_tree.md` 的 §2 映射表中的逻辑层条目生成完整 test task：

| layer | 来源 | 事务数 | 最少 scenario | 说明 |
|-------|------|:---:|:---:|------|
| backend_proc | logic 契约，sourceTask=backend 任务 | 0~1 | 2 (correct+error) | 单功能处理(jest.mock) |
| logic | 多个 logic 契约协作，sourceTask=主 backend 任务 | ≥2 或补偿 | 2 (correct+error) | 跨模块协作 |
| scenario | scenario 契约链，sourceTask=null | 交接点 | ≥2 (每交接点correct+error) | 跨模块数据交接(≤5步) |

🛑 **判定标准（按此严格分类，禁止混用）:**
  - 单功能、单 HTTP 端点、无跨模块数据传递 → **backend_proc** (jest.mock, 直调 service)
  - 跨多个功能/模块、≥2 事务、含补偿/回滚 → **logic** (supertest, HTTP串联)
  - 🛑 读操作(查询/列表/详情) → backend_proc。写操作含事务 → backend_proc。只有跨模块协作才是 logic。
  - 🛑 预计 backend_proc ~35 个（每 service 函数 1 个），logic ~10 个（仅事务链/补偿）。

## backend_proc — 单接口处理链

**范围**: 单个接口从收到请求到返回响应的完整处理链。1 个事务边界(BEGIN→COMMIT/ROLLBACK)。
**场景格式**: input(请求参数) + process(controller→service→SQL→返回 每一步) + output(响应+DB最终状态)
**依赖**: t_api_*（接口契约）+ t_dbapi_*（DB列验证）。🛑 不依赖 t_db_*（db_api 已封装 DDL）。

### 🛑 process 生成铁律（防止技术细节偏差）

**契约是唯一权威来源。process 中的技术操作必须从契约原文复制，禁止自己编造。**

| 你要描述的内容 | 从契约的哪个字段取 | 禁止 |
|--------------|------------------|------|
| 函数调用 | `serviceSignature.functionName` + `serviceSignature.params` | 禁止自己猜测参数格式（对象 vs 位置参数） |
| 参数名/顺序 | `serviceSignature.params[].name` 按顺序 | 禁止改参数名、禁止包装成对象 |
| Redis/DB 操作 | `process[].action` 原文 | 禁止把 INCR 写成 GET、把 DELETE 写成 DECR |
| key 前缀 | `process[].action` 中的实际 key 名 | 禁止改 sms:rate 为 sms:limit |
| TTL/阈值 | `process[].action` 中的实际数值 | 禁止改 60 为 300 |
| 错误码 | `errorMapping` 的 key | 禁止自己编造 TOO_MANY_SMS（契约是 SMS_RATE_LIMIT） |
| 回滚方式 | `rollback` 字段原文 | 禁止把 DELETE 描述为 DECR |
| 返回值字段 | `output` 字段 | 禁止添加契约不存在的字段 |

**简单原则：看到契约写什么就抄什么，不要"理解后重新表达"。契约写 INCR 就写 INCR，契约写 DELETE 就写 DELETE。**

### 🛑 生成每个 backend_proc 任务前，必须先输出参数提取表

**这是强制步骤。不输出参数表直接写 JSON 的，视为不合格输出。**

对每个 backend_proc 任务，先找到对应的 logic 契约，然后逐字段抄写参数表：

```
## 参数提取: {task_id} ← 契约 {contractId}

函数签名（从 serviceSignature 逐字抄）:
  functionName: {从 serviceSignature.functionName 抄}
  params (按顺序): {从 serviceSignature.params[].name 按顺序抄，可选参数标 ?}

错误码映射（从 errorMapping 逐字抄 key）:
  {errorMapping 的每个 key}

process 步骤（从 process[] 逐字抄 action + onFail.throw）:
  step1: {action 原文} → onFail: {throw 原文}
  step2: {action 原文} → onFail: {throw 原文}
  ...

回滚方式（从 rollback 逐字抄）:
  {rollback 原文}

边界来源:
  input.validation: {pattern/minLength/maxLength 原文}
  nfr.rateLimit: {window + max 原文}
```

**然后写 JSON 时，process 中的每一个技术术语必须与上表逐字一致。**

**示例：sendSmsCode 的参数表应该是这样（对应的 JSON 见下方）：**

```
## 参数提取: t_bp_send_sms_code ← 契约 logic_send_sms_code

函数签名:
  functionName: sendSmsCode
  params (按顺序): phone

错误码映射:
  INVALID_PHONE, SMS_RATE_LIMIT, SMS_SEND_FAILED

process 步骤:
  step1: 校验手机号格式 → onFail: INVALID_PHONE
  step2: Redis INCR sms:rate:{phone} EX 300 检查频率 → onFail: SMS_RATE_LIMIT
  step3: crypto.randomInt(100000, 999999) → 无 onFail
  step4: Redis SET sms:{phone}=code EX 60 → 无 onFail
  step5: 调用短信通道API发送 → onFail: SMS_SEND_FAILED

回滚方式:
  发送失败→DELETE Redis sms:{phone}

边界来源:
  input.validation: pattern=^1[3-9]\d{9}$
  nfr.rateLimit: window=5m, max=3
```

**示例：registerUser 的参数表应该是这样：**

```
## 参数提取: t_bp_register_user ← 契约 logic_register_user

函数签名:
  functionName: registerUser
  params (按顺序): phone, smsCode, password, ip?, device?

错误码映射:
  INVALID_PHONE, INVALID_PASSWORD_FORMAT, INVALID_SMS_CODE, SMS_CODE_INVALID, PHONE_REGISTERED, REGISTER_FAILED

process 步骤:
  step1: 校验手机号格式 → onFail: INVALID_PHONE
  step2: 校验密码格式 → onFail: INVALID_PASSWORD_FORMAT
  step3: Redis GET sms:{phone} 校验验证码 → onFail: SMS_CODE_INVALID
  step4: DELETE Redis sms:{phone} → 无 onFail
  step5: SELECT COUNT(1) FROM users WHERE phone=? → onFail: PHONE_REGISTERED
  step6: bcrypt.hash(password, 10) → 无 onFail
  step7: BEGIN TX → INSERT users → INSERT login_logs → COMMIT → onFail: REGISTER_FAILED

回滚方式:
  任一失败→ROLLBACK

边界来源:
  input.validation: phone.pattern=^1[3-9]\d{9}$, password.minLength=8, password.maxLength=64
```

🛑 **对比两个示例：sendSmsCode 无事务，registerUser 有事务。参数表的结构完全一样——都是把契约字段逐字抄到表里。每个 backend_proc 任务都必须先输出这样的表，再写 JSON。**
🛑 错误码必须是 errorMapping 的原始 key——不是自己用英文重新描述的变体。
🛑 process 中的 Redis 命令、key 名、TTL 值必须与契约 `process[].action` 原文一致。

```json
{
  "id": "t_bp_send_sms_code",
  "layer": "backend_proc",
  "testType": "logic",
  "sourceTask": "b_auth",
  "targetFiles": ["services/authService.js"],
  "dependencies": ["t_api_auth", "t_dbapi_auth"],
  "trunk": true,
  "testFramework": "jest",
  "description": "验证发送短信验证码的处理链：格式校验→频率限制→生成验证码→Redis缓存→短信通道",
  "note": "🛑 sourceTask=b_auth，对应契约 logic_send_sms_code",
  "testScenarios": [
    {
      "scenario": "发送验证码 — 正常发送",
      "category": "correct",
      "input": "phone='13800138000'",
      "process": [
        "controller: 验证 phone 格式（/^1[3-9]\\d{9}$/）",
        "🛑 从契约 serviceSignature 复制: authService.sendSmsCode(phone) — phone 是 string 位置参数",
        "🛑 从契约 process.step2 复制: Redis INCR sms:rate:{phone} EX 300 检查频率（≤3次/5min）",
        "🛑 从契约 process.step3 复制: crypto.randomInt(100000, 999999) 生成6位验证码",
        "🛑 从契约 process.step4 复制: Redis SET sms:{phone}=code EX 60 缓存验证码",
        "🛑 从契约 process.step5 复制: 调用短信通道API发送（mock模式固定123456）",
        "controller: 返回 {success:true}"
      ],
      "output": "200 {success:true}, Redis sms:{phone}=code TTL≈60"
    },
    {
      "scenario": "发送验证码 — 频率超限",
      "category": "error",
      "input": "phone='13800138000'（5分钟内已发3次）",
      "process": [
        "🛑 从契约 process.step2 复制: Redis INCR sms:rate:{phone} → count>3",
        "🛑 从契约 errorMapping 复制: throw SMS_RATE_LIMIT（不是 TOO_MANY_SMS）",
        "controller: catch → 429 {code:'SMS_RATE_LIMIT'}"
      ],
      "output": "429 SMS_RATE_LIMIT，未消耗配额"
    },
    {
      "scenario": "发送验证码 — 短信通道异常",
      "category": "error",
      "input": "phone='13800138001'，模拟短信通道超时",
      "process": [
        "🛑 从契约 process.step2~4 复制: INCR→SET 正常完成",
        "🛑 从契约 process.step5 复制: 调用短信通道 → 超时/异常",
        "🛑 从契约 rollback 字段复制: 失败→DELETE Redis sms:{phone}（不是 DECR sms:limit）",
        "🛑 从契约 errorMapping 复制: throw SMS_SEND_FAILED"
      ],
      "output": "500 SMS_SEND_FAILED，Redis 验证码已删除"
    }
  ]
}
```

🛑 **对比上一个版本的示例（t_bp_order）和这个版本（t_bp_send_sms_code）。新版本每条 process 都标注了从契约的哪个字段复制的。这是强制要求，不是可选的。**

🛑 逻辑层 scenario 必填: `category` + `input` + `process` + `output`。
🛑 category 取值: correct(正常流程) / error(事务回滚/异常) / boundary(边界输入) / state(非法状态转换)。
🛑 process 是步骤链，按 controller→service→SQL→返回 顺序。
🛑 **process 中的技术操作（Redis命令、key名、TTL、错误码）必须与契约原文一致，禁止重新表述。**

### 🛑 场景派生规则（从契约自动推导，不是自己构思）

**契约的 `process[].postCondition.onFail` 已经定义了所有异常路径。不需要你构思异常场景——逐条翻译 `onFail` 即可。**

```
1. correct 场景（1个）: 全部 process 步骤通过 → output 匹配
2. error 场景（N个）: 每个 process[].postCondition.onFail → 1 个 error scenario
3. rollback 场景: 如果契约有 rollback 字段 → 合并到触发步骤的 error scenario 中
```

**contract → scenarios 映射表：**

| 契约结构 | 对应的 scenario |
|---------|----------------|
| process（全部 steps 通过） | correct — {函数名}正常处理链 |
| process[].stepN.postCondition.onFail | error — {onFail.throw} 被抛出 |
| rollback | 附加到触发步骤的 error scenario 中作为清理验证 |
| errorMapping | 每个 key → error scenario 的错误码断言 |

**以 `sendSmsCode` 为例：**

```
契约 process:
  step1: onFail → INVALID_PHONE (422)
  step2: onFail → SMS_RATE_LIMIT (429)
  step3: 无 onFail
  step4: 无 onFail
  step5: onFail → SMS_SEND_FAILED (500)
rollback: 发送失败→DELETE Redis sms:{phone}

自动派生 scenarios:
  1. correct:      正常发送（全部通过）
  2. error:        INVALID_PHONE（step1 断点，无副作用）
  3. error:        SMS_RATE_LIMIT（step2 断点，无副作用）
  4. error:        SMS_SEND_FAILED（step5 断点 + DELETE 回滚验证）
```

🛑 **没有 `onFail` 的步骤不产生独立 error scenario。但相邻步骤之间可以合并**（如 step3+step4 都没有 onFail，它们的失败会传递到 step5）。

### 🛑 场景派生规则（续）— 边界覆盖

**仅靠 onFail 派生不够。还需要从 `input.validation` 和 `nfr` 派生边界场景。**

```
完整 scenario 清单 = 
  1 correct (全部通过)
  + N error (每个 onFail → 1 个)
  + M boundary (每个含 validation 的 input 字段 → 1~2 个)
  + K boundary (每个含阈值/窗口的 nfr → 1 个)
```

**`input.validation` → boundary 规则：**

| validation 类型 | boundary scenario | 断言 |
|----------------|-------------------|------|
| required: true | 空值/undefined → 抛 {errorCode} | `expect(() => fn()).toThrow(/{ERROR}/)` |
| pattern: "regex" | 2~3 个典型违反模式 | 同上 |
| minLength / maxLength | 极限值 ±1 | 同上 |

🛑 **每个 input 字段合并为 1 个 boundary scenario（不是每个违反模式一个）。一个 scenario 里 2~3 个 it() 块分别测不同违反模式。**

**`nfr` → boundary 规则：**

| nfr 类型 | boundary scenario | 断言 |
|---------|-------------------|------|
| rateLimit: {window, max} | 第 max 次成功 + 第 max+1 次拒绝 | 前 pass 后 throw |
| 其他阈值 | 阈值±1 | 前 pass 后 throw |

**以 `sendSmsCode` 为例，完整 scenario：**

```
1. correct:        正常发送（全部通过）
2. error:          INVALID_PHONE（step1 onFail）
3. error:          SMS_RATE_LIMIT（step2 onFail）
4. error:          SMS_SEND_FAILED + DELETE 回滚（step5 onFail + rollback）
5. boundary:       手机号格式边界（空值、非1开头、长度不对）← 从 input.validation 派生
6. boundary:       频率阈值边界（第3次通过、第4次拒绝）← 从 nfr.rateLimit 派生
```

🛑 **总计 target: 4~8 scenarios per backend_proc task。不是越多越好——边界过多说明 input 校验应该在 controller 层测。**

### 🛑 同层依赖（必须写在 dependencies 中）

**生成每个 backend_proc 任务时，必须检查：有没有前驱任务需要依赖？有就必须写。**

| 任务 | 必须依赖 | 原因 |
|------|---------|------|
| `t_bp_register_user` | — | 注册是入口 |
| `t_bp_login_by_phone` | `t_bp_register_user` | 注册产出 userId → 登录验证 |
| `t_bp_create_order` | `t_bp_login_by_phone` | 登录验证通过 → 下单信任会话 |
| `t_bp_create_payment` | `t_bp_create_order` | 下单产出 orderId → 支付需要 |
| `t_bp_apply_refund` | `t_bp_create_payment` | 支付产出 paymentId → 退款引用 |
| `t_bp_ship_order` | `t_bp_create_order` | 下单产出 orderId → 发货需要 |
| `t_bp_generate_settlement` | `t_bp_create_payment` | 支付完成 → 结算 |
| `t_bp_execute_refund` | `t_bp_audit_refund` | 审核通过 → 执行退款 |
| `t_bp_handle_payment_callback` | `t_bp_create_payment` | 支付先于回调 |
| 其余独立服务 | — | 不依赖其他 backend_proc |

🛑 **判断方法**：B 的参数来自 A 的返回 → B 依赖 A。如果 A 失败，B 的前置条件就不成立。
🛑 **生成完了逐条核对上表，缺了的补上。**

## logic — 功能间数据协作

**范围**: 单模块内多个功能之间的数据协作。≥2个事务边界或含补偿事务。
**场景格式**: input(初始状态) + process(功能间数据传递步骤) + output(最终数据一致性)
**依赖**: 只依赖 t_backendproc_*（backend_proc 已验证单服务正确）。
🛑 🛑 **logic 不穿透依赖 api/db_api/db**——backend_proc 已将 api+db_api 的验证结果封装为 services 真理。

```json
{
  "id": "t_logic_payment",
  "layer": "logic",
  "testType": "logic",
  "sourceTask": "b_payment",
  "targetFiles": ["routes/payment.js", "services/paymentService.js", "controllers/paymentController.js"],
  "dependencies": ["t_bp_create_payment", "t_bp_create_order"],
  "trunk": true,
  "testFramework": "jest+supertest",
  "description": "验证下单→支付的跨模块协作：支付成功后订单状态流转",
  "note": "来自 logic_create_order + logic_create_payment 协作，≥2个事务→logic层，sourceTask=b_payment",
  "testScenarios": [
    {
      "scenario": "下单 → 支付 — 支付成功后订单状态流转",
      "input": "已登录用户，已有 orderId=100(status='pending_pay')，支付金额=订单总金额",
      "process": [
        "POST /payment 支付 → 拿到 paymentId, paymentStatus='success'",
        "支付回调触发 → UPDATE orders SET status='paid'",
        "GET /order/100 查询 → 验证订单状态"
      ],
      "output": "order.status='paid', payment记录存在, 库存已扣减(不需要恢复)"
    }
  ]
}
```

🛑 logic 判定标准: process 步骤中 **≥2个事务边界** 或 **含补偿事务(SAGA)**

## scenario — 跨模块数据交接验证

**范围**: 2~4 个模块间的数据交接。不是全链路（太长发现在难定位）。
**场景格式**: input(起始状态) + process(模块A→模块B→模块C 数据传递步骤) + output(交接点数据一致性)
**依赖**: logic(已验证流程), api(全部端点)
🛑 **scenario 依赖各 `t_db_*`** — 确保种子数据已加载（测试用户/类目/商品），从 t_db_user/t_db_category 等真理获取种子数据

🛑 **每个 scenario 只覆盖 2~4 步跨模块数据交接**——注册→登录→浏览→下单 拆成多个短 scenario。
🛑 **步数 ≤5**，超了拆成新 scenario。短链好处：好定位问题、targetFiles 精简、可并行。

```json
{
  "id": "t_scenario_cart_order",
  "layer": "scenario",
  "testType": "logic",
  "sourceTask": null,
  "targetFiles": ["routes/cart.js", "controllers/cartController.js", "services/cartService.js",
                   "routes/order.js", "controllers/orderController.js", "services/orderService.js"],
  "dependencies": ["t_db_user", "t_db_cart", "t_db_order", "t_logic_create_order", "t_bp_add_cart", "t_bp_get_cart"],
  "trunk": true,
  "testFramework": "jest+supertest",
  "description": "验证 加购→下单 跨模块数据交接：cart 数据正确传入 order 模块",
  "note": "🛑 只覆盖 2~3 个模块的交接点，不是全链路。步数 ≤5",
  "testScenarios": [
    {
      "scenario": "cartItemId 交接 — order 内部重查 cart 后字段一致",
      "category": "correct",
      "input": "cart 加购产出: {cartItemId, skuId, quantity, price, productName}",
      "process": [
        "order 接收 cartItemIds → 内部用 cartItemId 重查 cart/service 获取详情",
        "→ order 使用的 productName/price/quantity 必须与 cart 原始值一致"
      ],
      "output": "order.items 的 productName/price/quantity = cart.items 的对应值"
    },
    {
      "scenario": "cartItemId 不存在 — order 拒绝",
      "category": "error",
      "input": "cartItemId=99999（不存在）",
      "process": [
        "order 接收 cartItemIds:[99999] → 内部重查 cart → 查不到",
        "→ 应拒绝创建订单"
      ],
      "output": "400/404, cart 原有数据不受影响"
    }
  ]
}
```
🛑 每个交接点 1 个 scenario = 1 个 it()。category 区分验证类型:
  correct(正常交接) / error(交接失败) / boundary(边界输入) / state(B不接受当前状态)
🛑 一个 it() 内完成: 设置模块A输入 → 验证模块A输出 → 执行交接处理 → 验证模块B输入 → 验证模块B输出。交接点是原子验证，不能拆开。

### scenario 场景速查表

```
买家短链:
  t_scenario_auth_catalog:     注册→登录(token交接)  登录→类目(token交接)  类目→列表(categoryId交接)
  t_scenario_search_detail:    搜索→详情(productId交接)
  t_scenario_detail_cart:      详情→加购(skuId交接)
  t_scenario_cart_order:       加购→下单(cartItemId+quantity+totalAmount交接)
  t_scenario_payment_flow:     下单→支付(orderId+amount交接)  支付→回调(paymentNo+sign交接)
  t_scenario_receive:          发货→收货(trackingNo交接)
  t_scenario_order_refund:     订单→退款(orderId→refundId交接)

商家短链:
  t_scenario_merchant_apply:   登录→入驻(token交接)  入驻→审核(merchantId交接)
  t_scenario_merchant_product: 发布→审核上架(productId交接)
  t_scenario_merchant_order:   接单→发货(orderId+trackingNo交接)  发货→统计(orderCount+revenue交接)

平台短链:
  t_scenario_platform_audit:   审核商家→审核商品(merchantId→productId关联)
  t_scenario_platform_ops:     报表→异常对账(totalAmount vs paidAmount)  异常→退款审核(abnormalId交接)

退款短链:
  t_scenario_refund:           申请→审核(refundId交接)  审核→执行(status交接)
```

🛑 scenario 无 sourceTask（来自 PRD 业务流程，非 task.json）。
🛑 scenario targetFiles = 涉及的 2~3 个模块文件，不是全依赖并集。

---

## 🛑 输出格式铁律

**JSON 文件只包含 tasks 数组。禁止附带任何元数据**（`counts`, `_meta`, `closures`, `rules_applied`, `contract_refs` 等）。这些都是 Agent 自检信息，不是测试任务数据。

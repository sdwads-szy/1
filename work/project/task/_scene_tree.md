# 场景树 — 星链商城 (StarChain Mall)

> Agent 可执行规范 | 从 PRD 提取，自上而下全局规划
> 生成时间: 2025-01

---

## §1 模块清单

| 编号 | 名称 | 主干/枝干 | 前台能力(API候选) | 后台能力(API候选) | 数据实体(表名) | 估算页面数 |
|------|------|----------|-------------------|-------------------|---------------|:---:|
| M1 | 商品浏览与发现 | 主干 | GET /api/products (商品列表/搜索/筛选), GET /api/products/:id (商品详情+SKU), GET /api/categories (类目树), GET /api/shops/:id (店铺信息) | — | spu, sku, product_images, categories, inventories | 4 |
| M2 | 商家商品管理 | 主干 | POST /api/merchants/register (入驻申请), GET /api/merchants/register/status (审核状态), GET/POST/PUT /api/merchant/products (商品CRUD), GET /api/merchant/orders (订单列表), POST /api/merchant/orders/:id/ship (发货), GET /api/merchant/refunds (售后列表), POST /api/merchant/refunds/:id/approve (售后审批), GET /api/merchant/dashboard (经营数据) | POST /api/admin/merchants/:id/review (商家审核), POST /api/admin/products/:id/review (商品审核) | merchants, shops, spu, sku, inventories | 8 |
| M3 | 订单与履约 | 主干 | POST /api/cart (加购/修改), GET /api/cart (购物车列表), POST /api/orders (下单), GET /api/orders/:id (订单详情), GET /api/orders (订单列表), POST /api/orders/:id/confirm (确认收货), POST /api/payments/pay (发起支付), GET /api/payments/status/:orderNo (支付状态) | GET /api/admin/orders (全局订单查询) | orders, sub_orders, order_items, payments, cart_items | 6 |
| M4 | 用户与鉴权 | 主干 | POST /api/auth/login (登录), POST /api/auth/register (注册), POST /api/auth/refresh (刷新Token), GET /api/user/profile (个人信息), GET/POST/PUT/DELETE /api/user/addresses (收货地址) | — | users, user_addresses, refresh_tokens | 3 |
| M5 | 平台运营后台 | 主干 | — | GET /api/admin/dashboard (数据看板), GET /api/admin/merchants (商家列表), POST /api/admin/merchants/:id/freeze (冻结/解冻), GET /api/admin/refunds/arbitration (仲裁工单), POST /api/admin/refunds/:id/arbitrate (仲裁裁决) | platform_daily_stats, merchant_daily_stats, operation_logs | 3 |
| B1 | 购物车 `←M1` | 枝干 | (共享M3购物车API) | — | cart_items | 0(共享) |
| B2 | 售后与仲裁 `←M3` | 枝干 | POST /api/refunds (发起售后), GET /api/refunds/:id (售后详情) | (共享M2/M5售后API) | refund_requests, refund_logs | 2 |
| B3 | 钱包与结算 `←M3` | 枝干 | GET /api/merchant/wallet (钱包余额), GET /api/merchant/settlements (结算单), POST /api/merchant/withdrawals (提现申请) | GET /api/admin/settlements (结算管理), POST /api/admin/settlements/:id/pay (打款), POST /api/admin/withdrawals/:id/approve (提现审批) | merchant_wallets, settlement_orders, withdrawal_requests, reconciliation_statements | 2 |
| B4 | 平台审核工作台 `←M2` | 枝干 | — | (共享M2/M5审核API) | (共享M2/M5实体) | 0(共享) |
| B5 | 物流 `←M3` | 枝干 | POST /api/merchant/orders/:id/ship (发货录单,共享M2) | GET /api/admin/logistics/monitor (物流监控) | shipments, shipment_events | 2 |

---

## §2 业务流程图 — Agent 决策树

### 链路 2.1: 消费者购物主链路 (Happy Path)

| 步骤 | 动作 | logic | api | 输入(字段+来源) | 输出(字段+去向) | 校验规则 | 错误码→Agent动作 | 事务边界 | 补偿路径 | 基础设施 |
|------|------|-------|-----|----------------|----------------|---------|-----------------|---------|---------|---------|
| S1 | 浏览首页/搜索商品 | logic_browse | GET /api/products?q=&cat=&sort=&page= → GET /api/categories | — | products[] → 列表渲染, categories[] → 导航 | query长度≤200, page≥1 | 400→提示"搜索词过长"; 500→显示降级缓存 | RO | — | Elasticsearch(降级:MySQL LIKE) |
| S2 | 查看商品详情 | logic_product_detail | GET /api/products/:id | productId:S1 | spu+skus[]+shop+images → 详情页渲染 | productId存在且status=已上架 | 404→"商品不存在或已下架",引导回首页 | RO | — | — |
| S3 | 选择SKU+数量→加入购物车 | logic_add_cart | POST /api/cart {skuId, quantity, shopId} | userId:token, skuId:S2, quantity:form, shopId:S2 | cartItem → B1 | 库存≥quantity, skuId属于当前spu | 401→redirect(/auth/login,preserve_state=true); 422 INSUFFICIENT_STOCK→读取availableStock,>0提示"仅剩N件",==0标记SKU不可选 | RW(cart_items) | — | — |
| S4 | 购物车勾选结算 | logic_cart_checkout | GET /api/cart → PATCH /api/cart/batch-check | userId:token, cartItemIds:勾选 | checkedCartItems[]→S5 | 勾选商品库存>0, 所属店铺未冻结 | 422 ITEM_UNAVAILABLE→过滤并提示"以下商品已失效:[name]",其余可继续结算 | RW(cart_items) | 失效商品自动uncheck | — |
| S5 | 下单结算 | logic_create_order | POST /api/orders {addressId, cartItemIds[], paymentMethod} | userId:token, addressId:address_book, cartItemIds:S4, paymentMethod:form | order{orderNo,subOrders[],totalAmount}→S6 | 地址非空, 每个sku库存≥quantity, 店铺状态=营业中 | 422 INSUFFICIENT_STOCK→释放所有预占,提示具体缺货商品; 422 SHOP_FROZEN→提示"店铺[shopName]已暂停营业" | 主订单+子订单+order_items+库存预占(单TX) | 下单失败→释放所有乐观锁预占库存 | — |
| S6 | 发起支付 | logic_pay | POST /api/payments/pay {orderNo, channel} | orderNo:S5, channel:form | paymentUrl/transactionNo→跳转支付页 | orderNo属于当前用户, status=待付款, 未超30min | 403→"无权操作此订单"; 408 TIMEOUT→"订单已超时,请重新下单",引导回S4 | payments INSERT | 支付超时30min→自动取消(见补偿链路2.5) | 支付网关SDK(mock) |
| S7 | 支付结果轮询 | logic_pay_status | GET /api/payments/status/:orderNo (轮询30s,间隔2s) | orderNo:S5 | status→{success:跳S9, fail:跳支付失败页, pending:继续轮询} | — | 30s超时→提示"支付结果确认中,稍后在订单列表查看" | RO | — | 支付网关SDK(mock) |
| S8 | 商家发货 | logic_ship | POST /api/merchant/orders/:id/ship {trackingNo, carrierCode} | subOrderId:order, trackingNo:物流单号, carrierCode:物流商 | shipment record | role=merchant, 订单属于本店, status=已付款 | 403→"无权操作"; 422 ORDER_STATUS→"当前订单状态不可发货" | shipment INSERT + sub_order status→已发货(TX) | — | 物流查询API(mock) |
| S9 | 确认收货 | logic_confirm_receive | POST /api/orders/:id/confirm | userId:token, orderId | order status→已完成 | order属于当前用户, status=已发货 | 403→"无权操作"; 409→"订单状态已变更,请刷新" | order status→已完成(TX) | — | — |

**Context 传递链**:
```
userId, token, role: S1→全链路 (token过期→refresh, 失败→回退S1登录)
productId: S1→S2, S3
cartItemIds: S4→S5 (S5校验时过滤已下架/库存不足商品并提示用户)
orderNo: S5→S6, S7, S8, S9
subOrderId: S5→S8
```

---

### 链路 2.2: 逆向售后链路

| 步骤 | 动作 | logic | api | 输入(字段+来源) | 输出(字段+去向) | 校验规则 | 错误码→Agent动作 | 事务边界 | 补偿路径 | 基础设施 |
|------|------|-------|-----|----------------|----------------|---------|-----------------|---------|---------|---------|
| R1 | 申请售后 | logic_refund_apply | POST /api/refunds {subOrderId, type, reason, amount, images[]} | userId:token, subOrderId:订单详情, type:only_refund/return_refund, reason:text, amount:decimal | refundRequest → R2 | subOrder属于当前用户, status∈{已付款,已发货,已完成}, 未超售后期 | 403→"无权操作"; 422 ALREADY_REFUNDING→"已有进行中的售后单"; 422 EXCEED_AMOUNT→"退款金额不可超过实付金额" | refund_requests INSERT(TX) | — | — |
| R2 | 商家审核 | logic_refund_review | POST /api/merchant/refunds/:id/approve {action, reason?} | merchantId:token, action:approve/reject, reason:text | result → R3a/R3b | role=merchant, 售后单属于本店 | 403→"无权操作"; 409→状态已变更 | refund_requests UPDATE(TX) | 超时24h(未发货)/72h(已发货)→自动同意 | — |
| R3a | 商家同意→退货/退款 | logic_refund_fulfill | 仅退款:立即退款; 退货退款:生成退货单 | — | refund status→退货中/退款中 | — | — | RW(refund_requests+payments退款) | 退款失败→retry_queue(3次指数退避) | 支付网关退款接口(mock) |
| R3b | 商家拒绝→平台仲裁 | logic_refund_arbitrate | POST /api/admin/refunds/:id/arbitrate {ruling, reason} | adminId:token, ruling:force_refund/dismiss | refund status→仲裁中→已完成/关闭 | role=admin | 403→"无权操作" | RW(refund_requests) | — | — |
| R4 | 退款完成 | — | (系统自动) | — | 库存恢复(退货退款), 佣金追索, 钱包扣减 | — | — | RW(inventories+merchant_wallets) | 追索失败→记录欠款至下期结算 | — |

**Context**: `subOrderId → refundRequestId`: R1→R4

---

### 链路 2.3: 商家入驻与经营链路

| 步骤 | 动作 | logic | api | 输入 | 输出 | 校验规则 | 错误码→Agent动作 | 事务边界 | 补偿路径 | 基础设施 |
|------|------|-------|-----|------|------|---------|-----------------|---------|---------|---------|
| M1 | 商家入驻申请 | logic_merchant_register | POST /api/merchants/register {step1:{mobile,code}, step2:{creditCode,bizLicense}, step3:{shopName,logo}} | 分步表单数据 | application → M2 | mobile唯一+验证码正确, creditCode唯一, shopName唯一 | 422 DUPLICATE_CREDIT_CODE→"该统一社会信用代码已被注册"; 422 DUPLICATE_SHOP_NAME→"店铺名已被占用" | merchants+shops申请记录INSERT(TX) | 草稿自动保存至localStorage | 短信通道API(验证码) |
| M2 | 平台审核 | logic_merchant_review | POST /api/admin/merchants/:id/review {action, reason} | adminId:token, action:approve/reject, reason | status→已开通/已驳回 | role=admin | 403→"无权操作" | merchants+shops status UPDATE(TX) | 超时48h→自动催办(邮件) | 邮件通知SMTP |
| M3 | 商品发布 | logic_product_publish | POST /api/merchant/products {spu, skus[], images[]} | merchantId:token | product→M4 | shop状态=营业中, sku价格>0 | 422 SHOP_FROZEN→"店铺已冻结,无法发布" | spu+sku INSERT(TX) | — | — |
| M4 | 商品审核 | logic_product_review | POST /api/admin/products/:id/review {action, reason} | adminId:token, action:approve/reject | product status→已上架/已驳回 | role=admin, 敏感词过滤 | 422 SENSITIVE_WORD→返回违规词列表 | spu status UPDATE | — | 敏感词过滤服务 |
| M5 | 经营数据查看 | logic_merchant_dashboard | GET /api/merchant/dashboard | merchantId:token | 实时指标+趋势图 | role=merchant | — | RO | — | — |

**Context**: `applicationId`: M1→M2, `productId`: M3→M4

---

### 链路 2.4: 平台运营主链路

| 步骤 | 动作 | logic | api | 输入 | 输出 | 校验规则 | 错误码→Agent动作 | 事务边界 | 补偿路径 | 基础设施 |
|------|------|-------|-----|------|------|---------|-----------------|---------|---------|---------|
| P1 | 数据看板 | logic_admin_dashboard | GET /api/admin/dashboard | adminId:token | 实时GMV/订单量/退款率/商家健康度 | role=admin | 500→显示上一小时缓存数据 | RO | — | 独立统计DB |
| P2 | 商家管理 | logic_admin_merchants | GET /api/admin/merchants → POST /api/admin/merchants/:id/freeze | adminId:token | 商家列表/冻结操作 | role=admin | 403→"无权操作" | merchants status UPDATE(TX) | 冻结→关联店铺商品立即下架 | — |
| P3 | 退款仲裁 | logic_arbitration | GET /api/admin/refunds/arbitration → POST /api/admin/refunds/:id/arbitrate | adminId:token, ruling | 仲裁裁决 | role=admin | 403→"无权操作"; 409→已处理 | refund_requests+payments(TX) | — | — |
| P4 | 结算打款 | logic_settlement_pay | GET /api/admin/settlements → POST /api/admin/settlements/:id/pay | adminId:token | 打款标注 | role=admin, settlement status=已确认 | 403→"无权操作" | settlement_orders UPDATE(TX) | — | 支付/银行API(mock) |

---

### 链路 2.5: 关键异常分支与补偿

#### 2.5.1 支付超时取消

```
order_timeout_cancel:
  触发: BullMQ延迟任务(order.created_at + 30min)
  基础设施: Redis + BullMQ
  步骤:
    1. SELECT status FROM orders WHERE order_no=? → 不是'待付款'则终止(幂等)
    2. BEGIN TX:
       UPDATE orders SET status='已取消' WHERE order_no=? AND status='待付款'
       FOR UPDATE sku JOIN order_items → UPDATE inventories SET stock=stock+qty, version=version+1
       COMMIT
    3. affected_rows==0 → ROLLBACK, 重试3次(间隔5s), 仍失败→告警
    4. 支付网关关单(失败不影响主流程, 记录retry_queue)
```

#### 2.5.2 支付回调丢失

```
payment_callback_lost:
  触发: 定时任务(每5min)
  基础设施: 支付网关SDK
  步骤:
    1. SELECT * FROM payments WHERE status='待支付' AND created_at < NOW()-5min
    2. 逐条调用支付网关查询订单状态
    3. 已支付→更新order状态+释放预占库存标记; 已关单→cancel流程
    4. 最多查询12次(1小时), 仍无结果→人工对账
```

#### 2.5.3 库存并发冲突

```
inventory_concurrency:
  触发: 下单时乐观锁version冲突
  步骤:
    1. UPDATE inventories SET stock=stock-?, version=version+1 WHERE sku_id=? AND shop_id=? AND version=? AND stock>=?
    2. affected_rows==0 → 重试(最多3次, 指数退避100ms/200ms/400ms)
    3. 3次均失败 → 返回422 INSUFFICIENT_STOCK, 提示用户刷新
```

#### 2.5.4 结算超额提现

```
withdrawal_overflow:
  触发: 提现申请提交
  步骤:
    1. BEGIN TX: SELECT balance, version FROM merchant_wallets WHERE merchant_id=?
    2. balance < withdrawal_amount → ROLLBACK, 返回422 "余额不足,可提余额:¥{balance}"
    3. UPDATE merchant_wallets SET balance=balance-?, frozen_balance=frozen_balance+?, version=version+1 WHERE version=?
    4. version冲突 → 提示"余额已变动,请刷新重试"
```

---

### 外部依赖降级策略

| 依赖 | 正常路径 | 降级路径 | Agent 处理 |
|------|---------|---------|-----------|
| 支付网关 | 异步回调通知 | 回调丢失 | 定时主动查单(每5min, 最多12次); 用户端轮询30s; 人工对账补单 |
| 物流查询API | 实时轨迹查询 | 查询失败/超时 | 显示"物流信息更新中", 不阻塞确认收货; 商家手动录入单号 |
| 搜索服务(ES) | 全文索引搜索 | 服务宕机 | 降级为MySQL LIKE查询 |
| 数据看板实时模块 | Redis实时指标 | 模块失败 | 显示上一小时缓存数据 |
| 敏感词过滤 | API实时检测 | 服务超时 | 标记"机审跳过", 进入人工审核队列 |
| 邮件通知(SMTP) | 审核结果/催办通知 | 发送失败 | 记录通知失败日志, 后台可手动重发 |

---

## §3 数据实体地图

### §3.1 实体关系

```
users       (1) ──< (N) user_addresses
users       (1) ──< (N) orders
users       (1) ──< (N) cart_items
users       (N) ──< (1) merchants (一个用户可以是商家)
merchants   (1) ──< (1) shops
shops       (1) ──< (N) spu
spu         (1) ──< (N) sku
spu         (1) ──< (N) product_images
sku         (1) ──< (1) inventories (per shop)
categories  (1) ──< (N) categories (自引用树)
orders      (1) ──< (N) sub_orders
sub_orders  (1) ──< (N) order_items
sub_orders  (1) ──< (1) payments
sub_orders  (1) ──< (1) shipments
sub_orders  (1) ──< (N) refund_requests
shops       (1) ──< (1) merchant_wallets
merchant_wallets (1) ──< (N) withdrawal_requests
merchants   (1) ──< (N) settlement_orders
```

### §3.2 实体摘要

| 实体 | 关键字段 | FK | 状态机 |
|------|---------|----|--------|
| **users** | id, mobile, role(ENUM:user/merchant/admin), password_hash, status | — | active/disabled |
| **user_addresses** | id, user_id, province/city/district/detail, phone, is_default | user_id→users | — |
| **merchants** | id, user_id, credit_code(UNIQUE), contact_name, status | user_id→users | 待审核→已开通→已禁用 |
| **shops** | id, merchant_id(UNIQUE), name(UNIQUE), logo, status | merchant_id→merchants | 营业中/已打烊/已冻结 |
| **spu** | id, shop_id, category_id, name, status, sales | shop_id→shops, category_id→categories | 草稿→已上架→已下架 |
| **sku** | id, spu_id, spec_name, price(DECIMAL), image | spu_id→spu | (随spu) |
| **inventories** | id, sku_id, shop_id, stock(INT), frozen_stock(INT), version | sku_id→sku, shop_id→shops | — (乐观锁) |
| **categories** | id, parent_id, name, level, sort | parent_id→categories(自引用) | — |
| **cart_items** | id, user_id, sku_id, shop_id, quantity, checked | user_id→users, sku_id→sku, shop_id→shops | — |
| **orders** | id, order_no(UNIQUE), user_id, total_amount(DECIMAL), status, paid_at | user_id→users | 见§3.4 |
| **sub_orders** | id, sub_order_no(UNIQUE), order_id, shop_id, amount, status | order_id→orders, shop_id→shops | 随主订单联动 |
| **order_items** | id, sub_order_id, sku_id, quantity, price, snapshot(JSON) | sub_order_id→sub_orders | — |
| **payments** | id, transaction_no(UNIQUE), sub_order_id, channel, amount, status, callback_log | sub_order_id→sub_orders | pending→success/failed/refunded |
| **shipments** | id, sub_order_id, tracking_no, carrier_code, status | sub_order_id→sub_orders | 待揽收→运输中→已签收/已退回 |
| **refund_requests** | id, request_no(UNIQUE), sub_order_id, type, amount, status, reason | sub_order_id→sub_orders | 见§3.4 |
| **merchant_wallets** | id, merchant_id(UNIQUE), balance(DECIMAL), frozen_balance(DECIMAL), version | merchant_id→merchants | — (乐观锁) |
| **settlement_orders** | id, merchant_id, period(UNIQUE with merchant_id), amount, status | merchant_id→merchants | 待确认→已确认→已打款→已完成 / 已追索 |
| **withdrawal_requests** | id, request_no(UNIQUE), merchant_id, amount, status | merchant_id→merchants | pending→approved→paid / rejected |

**支持表**:

| 实体 | 关键字段 | FK | 说明 |
|------|---------|----|------|
| **product_images** | id, spu_id, url, sort | spu_id→spu | 商品图片 |
| **refund_logs** | id, refund_request_id, operator_id, action, detail | refund_request_id→refund_requests | 售后操作日志 |
| **shipment_events** | id, shipment_id, event, timestamp, location | shipment_id→shipments | 物流轨迹 |
| **refresh_tokens** | id, user_id, token_hash(UNIQUE), expires_at | user_id→users | JWT刷新令牌 |
| **platform_daily_stats** | id, stat_date(UNIQUE), gmv, order_count, refund_rate, commission | — | 平台日统计 |
| **merchant_daily_stats** | id, merchant_id, stat_date(UNIQUE with merchant_id), gmv, order_count | merchant_id→merchants | 商家日统计 |
| **operation_logs** | id, admin_id, action, target_type, target_id, detail | admin_id→users | 运营操作日志 |
| **reconciliation_statements** | id, merchant_id, date(UNIQUE with merchant_id), diff | merchant_id→merchants | 对账差异 |

### §3.3 关键约束

| 约束类型 | 表 | 字段 | 说明 |
|---------|----|------|------|
| UNIQUE | users | (mobile, tenant_id) | 手机号租户内唯一 |
| UNIQUE | merchants | credit_code | 统一社会信用代码唯一 |
| UNIQUE | shops | merchant_id | 一商一店 |
| UNIQUE | shops | name | 店名唯一 |
| UNIQUE | orders | order_no | 主订单号唯一 |
| UNIQUE | sub_orders | sub_order_no | 子订单号唯一 |
| UNIQUE | payments | transaction_no | 支付流水号唯一 |
| UNIQUE | inventories | (sku_id, shop_id) | 每店铺每SKU一条库存记录 |
| UNIQUE | refund_requests | (sub_order_id, request_no) | 子订单+售后单号唯一 |
| UNIQUE | settlement_orders | (merchant_id, period) | 每商家每周期一条结算单 |
| UNIQUE | withdrawal_requests | (merchant_id, request_no) | 提现单号唯一 |
| FK | orders | user_id→users | 订单归属 |
| FK | sub_orders | shop_id→shops | 子订单归属店铺 |
| FK | cart_items | user_id→users | 购物车归属 |
| 加密 | users | mobile, password_hash | bcrypt加密, 手机号脱敏 |
| 加密 | user_addresses | phone, detail | 传输加密, 日志脱敏 |
| 金额 | 全部金额字段 | — | DECIMAL(12,2) 或 INT(分), 禁止浮点数 |

### §3.4 状态机矩阵

```
orders.status:
  pending      → pay_success: paid (支付成功回调)
  pending      → user_cancel: cancelled (用户手动取消)
  pending      → timeout: cancelled (30min超时自动取消)
  paid         → ship: shipped (商家全部发货)
  paid         → refund_apply: refunding (申请售后)
  shipped      → confirm_receive: completed (用户确认收货)
  shipped      → auto_receive: completed (7天自动确认)
  shipped      → refund_apply: refunding (申请退货退款)
  completed    → refund_apply: refunding (申请售后)
  cancelled, refunded → 终态(不可变更)

refund_requests.status:
  pending       → merchant_approve: awaiting_return (商家同意, 仅退款则→refunding)
  pending       → merchant_reject: rejected (商家拒绝)
  pending       → auto_approve: awaiting_return (超时未审核自动同意)
  awaiting_return → user_shipped: awaiting_merchant_receive (用户发货)
  awaiting_merchant_receive → merchant_confirm: refunding (商家确认收货)
  refunding     → callback_success: completed (退款到账)
  refunding     → callback_fail: retry (退款失败重试)
  rejected      → platform_arbitrate: arbitrating (消费者申请平台介入)
  arbitrating   → force_refund: refunding (平台强制退款)
  arbitrating   → dismiss: closed (平台驳回)
  completed, closed → 终态(不可变更)

settlement_orders.status:
  pending       → confirm: confirmed (商家确认)
  confirmed     → pay: paid (平台打款)
  paid          → complete: completed (到账确认)
  any_active    → clawback: clawed_back (退款追索)
```

### §3.5 并发策略

| 场景 | 策略 | 参数 |
|------|------|------|
| 下单扣库存 | 乐观锁 CAS (version字段) | 重试3次, 指数退避 100ms/200ms/400ms |
| 提现余额扣减 | 乐观锁 CAS (version字段) | 版本冲突→提示"余额已变动,请刷新" |
| 购物车修改 | 行级锁 | UPDATE cart_items WHERE user_id=? AND sku_id=? AND shop_id=? |
| 退款追索 | 悲观锁 SELECT FOR UPDATE | 锁定wallet行, 等锁3s |

---

## §4 页面导航图

| 文件路径 | 路由 | 说明 | scope | 从哪来→到哪去 | ui_style | 性能要求 |
|---------|------|------|-------|--------------|----------|---------|
| src/pages/home/index.vue | / | 首页: 商品瀑布流、Banner、分类icon、店铺推荐 | consumer | ←搜索页/商详返回; →搜索页/商详/分类 | browse-search | — |
| src/pages/search/index.vue | /search | 全局搜索、关键词联想、筛选排序 | consumer | ←首页; →商详 | browse-search | 搜索响应P99<500ms |
| src/pages/category/list.vue | /category/:id | 按分类浏览、多条件筛选 | consumer | ←首页; →商详 | browse-search | 列表P99<500ms |
| src/pages/product/detail.vue | /product/:id | 主图轮播、SKU选择、店铺信息 | consumer | ←首页/搜索/分类; →购物车/下单 | browse-search | 详情P99<300ms |
| src/pages/cart/index.vue | /cart | 购物车: 勾选结算、分组、失效提醒 | consumer | ←商详; →下单结算 | order-management | — |
| src/pages/checkout/index.vue | /checkout | 下单结算: 地址、确认订单、支付方式 | consumer | ←购物车; →支付页 | order-management | 创建订单<1s |
| src/pages/checkout/pay.vue | /checkout/pay | 支付结果轮询、超时引导 | consumer | ←结算页; →订单详情/订单列表 | order-management | — |
| src/pages/orders/list.vue | /orders | 我的订单列表、多状态Tab | consumer | ←支付结果/个人中心; →订单详情 | order-management | — |
| src/pages/orders/detail.vue | /orders/:id | 订单详情、物流进度、操作按钮 | consumer | ←订单列表; →售后申请 | order-management | — |
| src/pages/orders/refund/apply.vue | /orders/:id/refund | 售后申请: 类型、原因、金额、凭证 | consumer | ←订单详情; →售后详情 | order-management | — |
| src/pages/orders/refund/detail.vue | /orders/:id/refund/detail | 售后详情、状态进度、协商记录 | consumer | ←售后申请/订单详情; →仲裁入口 | order-management | — |
| src/pages/auth/login.vue | /auth/login | 消费者登录注册、手机验证码 | consumer | ←任意需登录页; →来源页 | user-account | — |
| src/pages/user/profile.vue | /user/profile | 个人信息、收货地址管理 | consumer | ←个人中心入口; →地址管理 | user-account | — |
| src/pages/admin/login.vue | /admin/login | 商家/平台独立后台登录入口 | merchant+admin | ←后台入口; →商家后台/平台后台 | user-account | — |
| src/pages/merchant/register/index.vue | /merchant/register | 商家入驻分步表单 | merchant | ←平台入口; →审核状态页 | merchant-onboarding | — |
| src/pages/merchant/register/status.vue | /merchant/register/status | 审核进度、驳回明细 | merchant | ←入驻提交; →商家后台(通过后) | merchant-onboarding | — |
| src/pages/merchant/products/list.vue | /merchant/products | 商品列表、发布/编辑/下架 | merchant | ←商家后台首页; →商品编辑 | merchant-product-management | — |
| src/pages/merchant/orders/list.vue | /merchant/orders | 多状态筛选、发货处理 | merchant | ←商家后台; →发货页/订单详情 | order-management | — |
| src/pages/merchant/orders/shipping.vue | /merchant/orders/:id/shipping | 物流单号录入 | merchant | ←订单列表; →订单列表(返回) | order-management | — |
| src/pages/merchant/refunds/list.vue | /merchant/refunds | 售后审批列表 | merchant | ←商家后台; →售后详情 | order-management | — |
| src/pages/merchant/dashboard/index.vue | /merchant/dashboard | 经营数据: 实时指标、趋势图 | merchant | ←商家后台首页 | merchant-settlement | — |
| src/pages/merchant/wallet/index.vue | /merchant/wallet | 钱包余额、结算单、提现申请 | merchant | ←商家后台; →结算详情 | merchant-settlement | — |
| src/pages/admin/dashboard/index.vue | /admin/dashboard | 平台数据看板: GMV/订单/退款率 | admin | ←平台后台首页 | admin-platform-analytics | — |
| src/pages/admin/merchants/review.vue | /admin/merchants/review | 商家入驻审核 | admin | ←平台后台; →商家列表 | admin-review-dashboard | — |
| src/pages/admin/merchants/index.vue | /admin/merchants | 商家列表、冻结/解冻管理 | admin | ←平台后台; →审核页 | admin-review-dashboard | — |
| src/pages/admin/products/review.vue | /admin/products/review | 商品审核、敏感词过滤结果 | admin | ←平台后台; →商品列表 | admin-review-dashboard | — |
| src/pages/admin/orders/list.vue | /admin/orders | 全局订单查询 | admin | ←平台后台; →订单详情 | order-management | — |
| src/pages/admin/refunds/arbitration.vue | /admin/refunds/arbitration | 退款仲裁工作台 | admin | ←平台后台 | admin-review-dashboard | — |
| src/pages/admin/finance/settlements.vue | /admin/finance/settlements | 结算审核、打款操作 | admin | ←平台后台 | merchant-settlement | — |
| src/pages/admin/logistics/index.vue | /admin/logistics | 物流商配置、接口异常监控 | admin | ←平台后台 | ? | — |

> 🛑 **总页面数: 30**。ui_style=`?` (1个): admin/logistics 无匹配UI文档，该页面为监控仪表盘类型，最接近 `admin-platform-analytics`。

---

## §5 鉴权需求

| 维度 | 值 |
|------|----|
| **Token类型** | JWT |
| **Payload** | `{userId: int, role: "user"\|"merchant"\|"admin", iat, exp}` |
| **access_token** | 有效期 15min, 存内存 |
| **refresh_token** | 有效期 7d, HttpOnly Secure SameSite=Strict Cookie |
| **传输方式** | Authorization: Bearer {token}, 全站HTTPS |
| **密码存储** | bcrypt, saltRounds=10 |
| **中间件链** | `authenticate` → 401 → redirect /auth/login; `requireRole(role)` → 403 → 提示无权访问 |
| **路由守卫** | `/cart`, `/checkout`, `/orders/*`, `/user/*` → requiresAuth(role=user)<br>`/merchant/*` → requiresMerchant(role=merchant)<br>`/admin/*` → requiresAdmin(role=admin) |
| **数据所有权** | 消费者只能查看自己的订单/购物车/地址; 商家只能管理自己店铺的商品/订单/售后; 平台管理员可查看全部 |
| **敏感操作** | 支付回调→RSA验签; 提现→二次确认+短信验证 |
| **Token刷新** | 401响应 → 前端自动调用 POST /api/auth/refresh (携带Cookie refresh_token) → 成功则更新内存token并重试原请求 → 失败则清除状态跳转登录页 |
| **手机验证码** | 注册/登录/换绑手机, 有效期5min, 同手机号60s内不可重复发送 |

---

## §6 契约预估

| 契约类型 | 预估数量 | 依据 |
|---------|:---:|------|
| model | 26 | 18核心实体 + 8支持表 |
| auth | 1 | JWT鉴权中间件+角色守卫 |
| scenario | 5 | 4条主链路 + 1条异常补偿链路 |
| logic | 18 | 流程节点 ≥ 总步骤/2 ≈ 36/2 |
| api | 35 | 模块表中所有去重API候选 |
| db-api | 26 | 至少每个实体1个CRUD操作(去重) |
| navigation | 45 | 页面间跳转关系对数 |
| tasks | 34 | infra(10) + db(26) + frontend(35) + backend(35) + integration(1) |

**契约内部分布预估**:
- model: 26 (含8个支持表: product_images, refund_logs, shipment_events, refresh_tokens, platform_daily_stats, merchant_daily_stats, operation_logs, reconciliation_statements)
- api: 35 (M1:4 + M2:10 + M3:8 + M4:7 + M5:5 + B2:2 + B3:5 + B5:2, 去重后)
- db-api: 26 (每实体≥1个核心查询操作)
- logic: 18 (S1~S9, R1~R4, M1~M5, P1~P4, +异常补偿4 去重)

---

## §7 覆盖计数表

| 维度 | 应有数量 | 实际数量 | 覆盖? |
|------|:---:|:---:|:---:|
| 模块(主干) | 5 (M1~M5) | 5 | ✅ |
| 数据实体 | 18 (PRD §7) | 26 (18核心+8支持) | ✅ |
| 业务链路 | ≥5 | 5 (消费者购物+逆向售后+商家入驻+平台运营+异常补偿) | ✅ |
| 流程节点(logic候选) | ~8 | 18 (含S/R/M/P+异常补偿) | ✅ |
| API候选 | ≥5 | 35 (去重后) | ✅ |
| 页面 | ~15 (PRD估计) | 30 (实际文件路径去重) | ✅ |
| NFR维度 | 7 (PRD §6) | 7: 性能/并发/安全/可用性/兼容性/扩展性/降级 | ✅ |
| ── 接口层预估（Step 2 自检用）── | | | |
| api 契约数 | ≥35 (§1模块表去重API候选) | — (Step 2生成) | — |
| db-api 契约数 | ≥26 (§2流程中去重DB操作+每实体≥1) | — (Step 2生成) | — |
| navigation 契约数 | ≥45 (§4页面跳转对数) | — (Step 2生成) | — |
| auth 契约数 | 1 (有鉴权需求) | — (Step 2生成) | — |

---

**[场景树完成]** ✅ 全部 §7 维度覆盖确认通过，无 ❌ 项。

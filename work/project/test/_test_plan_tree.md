# 测试规划树 — 星链商城 (StarChain Mall)

> 生成时间: 2025-01 | 输入: PRD + 场景树 + 业务契约(scenario+logic) + 任务骨架
> 后续各层 Agent 只读此树生成具体 test task，不再读取原始 PRD/场景树/契约/骨架。

---

## §1 输入摘要

| 指标 | 值 |
|------|-----|
| 骨架任务总数 | 81 (infra 10 + db 25 + frontend 21 + backend 24 + integ 1) |
| 预计测试任务总数 | 172 (静态层 81 + 接口层 51 + 逻辑层 31 + 质量层 9) |
| 业务契约 | 5 scenario + 26 logic + 26 api + 73 db_api + 26 model |
| NFR 维度 | 7 (性能/并发与容量/安全/可用性/兼容性/扩展性/降级策略) |
| 核心业务流程 | 5 条（消费者购物 + 逆向售后 + 商家入驻经营 + 平台运营 + 异常补偿） |
| 数据实体 | 26 (18 核心 + 8 支持表) |
| 页面数 | 30 个页面，~45 组相邻跳转 |
| 第三方服务 | 3 (支付/银行API mock/real、物流查询API mock/real、邮件SMTP) |

> 🛑 预计测试任务总数 172 ≥ 骨架任务总数 81 ✅

---

## §2 逐层映射表

---

### 静态层

#### Infra (10)

| testId | layer | sourceTask | targetFiles | dependencies | ui_style | 备注 |
|--------|-------|-----------|-------------|-------------|----------|------|
| t_infra_package | infra | infra_package | package.json | — | — | 检查 name/version/scripts/dependencies 结构 |
| t_infra_env | infra | infra_env | .env, .env.example, .env.development, .env.production | t_infra_config | — | 检查必填环境变量: DB_*, REDIS_*, JWT_SECRET, SMTP_*, PAYMENT_MODE, LOGISTICS_MODE, *_API_KEY |
| t_infra_config | infra | infra_config | config/db.js, config/logger.js, config/redis.js | t_infra_package | — | 检查导出(db/pool/redis/logger)完整性 |
| t_infra_utils | infra | infra_utils | utils/response.js, utils/encryption.js, utils/snowflake.js | — | — | 检查工具函数导出 |
| t_infra_middleware | infra | infra_middleware | middleware/auth.js, middleware/permission.js, middleware/errorHandler.js | t_infra_config, t_infra_utils | — | 检查 authenticate/requireRole/errorHandler 导出 |
| t_infra_app | infra | infra_app | app.js | t_infra_config, t_infra_middleware | — | 检查 Express 初始化+中间件注册链 |
| t_infra_frontend_core | infra | infra_frontend_core | src/main.js, src/App.vue, src/router/index.js | — | — | 检查 Vue 初始化+路由注册 |
| t_infra_frontend_config | infra | infra_frontend_config | vite.config.js, index.html | — | — | 检查 Vite 配置+HTML 入口 |
| t_infra_api | infra | infra_api | src/utils/request.js | — | — | 检查 axios 实例+拦截器 |
| t_infra_stores | infra | infra_stores | src/stores/user.js, src/stores/cart.js | t_infra_api | — | 检查 Pinia store 定义 |

#### DB (25)

| testId | layer | sourceTask | targetFiles | dependencies | ui_style | 备注 |
|--------|-------|-----------|-------------|-------------|----------|------|
| t_db_users | db | db_tables_users | database/schema/users.sql, database/seed/users.json, database/seed/refresh_tokens.json | t_infra_config | — | FK→无（根表）; seed 含 refresh_tokens |
| t_db_user_addresses | db | db_tables_user_addresses | database/schema/user_addresses.sql, database/seed/user_addresses.json | t_db_users | — | FK→users.id |
| t_db_merchants | db | db_tables_merchants | database/schema/merchants.sql, database/seed/merchants.json | t_db_users | — | FK→users.id; credit_code UNIQUE |
| t_db_shops | db | db_tables_shops | database/schema/shops.sql, database/seed/shops.json | t_db_merchants | — | FK→merchants.id; merchant_id UNIQUE |
| t_db_categories | db | db_tables_categories | database/schema/categories.sql, database/seed/categories.json | — | — | FK→无; parent_id 自引用 |
| t_db_spu | db | db_tables_spu | database/schema/spu.sql, database/seed/spu.json | t_db_shops, t_db_categories | — | FK→shops.id, categories.id |
| t_db_sku | db | db_tables_sku | database/schema/sku.sql, database/seed/sku.json | t_db_spu | — | FK→spu.id |
| t_db_inventories | db | db_tables_inventories | database/schema/inventories.sql, database/seed/inventories.json | t_db_sku, t_db_shops | — | FK→sku.id, shops.id; (sku_id,shop_id) UNIQUE; version 乐观锁 |
| t_db_product_images | db | db_tables_product_images | database/schema/product_images.sql, database/seed/product_images.json | t_db_spu | — | FK→spu.id |
| t_db_cart_items | db | db_tables_cart_items | database/schema/cart_items.sql, database/seed/cart_items.json | t_db_users, t_db_sku, t_db_shops | — | FK→users.id, sku.id, shops.id |
| t_db_orders | db | db_tables_orders | database/schema/orders.sql, database/seed/orders.json | t_db_users | — | FK→users.id; order_no UNIQUE |
| t_db_sub_orders | db | db_tables_sub_orders | database/schema/sub_orders.sql, database/seed/sub_orders.json | t_db_orders, t_db_shops | — | FK→orders.id, shops.id; sub_order_no UNIQUE |
| t_db_order_items | db | db_tables_order_items | database/schema/order_items.sql, database/seed/order_items.json | t_db_sub_orders | — | FK→sub_orders.id; snapshot JSON |
| t_db_payments | db | db_tables_payments | database/schema/payments.sql, database/seed/payments.json | t_db_sub_orders | — | FK→sub_orders.id; transaction_no UNIQUE |
| t_db_shipments | db | db_tables_shipments | database/schema/shipments.sql, database/seed/shipments.json | t_db_sub_orders | — | FK→sub_orders.id |
| t_db_shipment_events | db | db_tables_shipment_events | database/schema/shipment_events.sql, database/seed/shipment_events.json | t_db_shipments | — | FK→shipments.id |
| t_db_refund_requests | db | db_tables_refund_requests | database/schema/refund_requests.sql, database/seed/refund_requests.json | t_db_sub_orders | — | FK→sub_orders.id; (sub_order_id,request_no) UNIQUE |
| t_db_refund_logs | db | db_tables_refund_logs | database/schema/refund_logs.sql, database/seed/refund_logs.json | t_db_refund_requests | — | FK→refund_requests.id |
| t_db_merchant_wallets | db | db_tables_merchant_wallets | database/schema/merchant_wallets.sql, database/seed/merchant_wallets.json | t_db_merchants | — | FK→merchants.id; merchant_id UNIQUE; version 乐观锁 |
| t_db_settlement_orders | db | db_tables_settlement_orders | database/schema/settlement_orders.sql, database/seed/settlement_orders.json | t_db_merchants | — | FK→merchants.id; (merchant_id,period) UNIQUE |
| t_db_withdrawal_requests | db | db_tables_withdrawal_requests | database/schema/withdrawal_requests.sql, database/seed/withdrawal_requests.json | t_db_merchants | — | FK→merchants.id; (merchant_id,request_no) UNIQUE |
| t_db_platform_daily_stats | db | db_tables_platform_daily_stats | database/schema/platform_daily_stats.sql, database/seed/platform_daily_stats.json | — | — | FK→无; stat_date UNIQUE |
| t_db_merchant_daily_stats | db | db_tables_merchant_daily_stats | database/schema/merchant_daily_stats.sql, database/seed/merchant_daily_stats.json | t_db_merchants | — | FK→merchants.id; (merchant_id,stat_date) UNIQUE |
| t_db_operation_logs | db | db_tables_operation_logs | database/schema/operation_logs.sql, database/seed/operation_logs.json | t_db_users | — | FK→users.id(admin_id) |
| t_db_reconciliation_statements | db | db_tables_reconciliation_statements | database/schema/reconciliation_statements.sql, database/seed/reconciliation_statements.json | t_db_merchants | — | FK→merchants.id; (merchant_id,date) UNIQUE |

🛑 seed 检查已并入各 t_db_* 任务（targetFiles 含 seed 文件），不单独建 t_db_seed。

#### Frontend (21)

| testId | layer | sourceTask | targetFiles | dependencies | ui_style | 备注 |
|--------|-------|-----------|-------------|-------------|----------|------|
| t_frontend_product_browse | frontend | f_product_browse | src/api/products.js, src/pages/home/index.vue, src/pages/search/index.vue, src/pages/category/list.vue, src/pages/product/detail.vue | t_db_spu, t_db_sku, t_db_categories, t_db_shops, t_infra_frontend_core, t_infra_api, t_infra_stores | browse-search | v-model→spu/sku/categories/shops.fields |
| t_frontend_cart | frontend | f_cart | src/api/cart.js, src/pages/cart/index.vue | t_frontend_product_browse, t_db_cart_items, t_infra_frontend_core, t_infra_api, t_infra_stores | order-management | v-model→cart_items.fields |
| t_frontend_checkout | frontend | f_checkout | src/api/orders.js, src/api/payments.js, src/api/user-addresses.js, src/pages/checkout/index.vue, src/pages/checkout/pay.vue | t_frontend_cart, t_db_orders, t_db_user_addresses, t_infra_frontend_core, t_infra_api, t_infra_stores | order-management | v-model→orders/addresses.fields |
| t_frontend_orders | frontend | f_orders | src/pages/orders/list.vue, src/pages/orders/detail.vue | t_frontend_checkout, t_db_orders, t_db_sub_orders, t_infra_frontend_core, t_infra_api, t_infra_stores | order-management | v-model→orders/sub_orders.fields |
| t_frontend_refunds | frontend | f_refunds | src/api/refunds.js, src/pages/orders/refund/apply.vue, src/pages/orders/refund/detail.vue | t_frontend_orders, t_db_refund_requests, t_infra_frontend_core, t_infra_api, t_infra_stores | order-management | v-model→refund_requests.fields |
| t_frontend_auth | frontend | f_auth | src/api/auth.js, src/pages/auth/login.vue | t_infra_frontend_core, t_infra_api, t_infra_stores | user-account | v-model→auth form fields |
| t_frontend_user_profile | frontend | f_user_profile | src/api/user.js, src/pages/user/profile.vue | t_frontend_auth, t_db_users, t_db_user_addresses, t_infra_frontend_core, t_infra_api, t_infra_stores | user-account | v-model→users/addresses.fields |
| t_frontend_admin_auth | frontend | f_admin_auth | src/pages/admin/login.vue | t_frontend_auth, t_infra_frontend_core, t_infra_api, t_infra_stores | user-account | 商家/平台后台登录入口 |
| t_frontend_merchant_register | frontend | f_merchant_register | src/api/merchant-register.js, src/pages/merchant/register/index.vue, src/pages/merchant/register/status.vue | t_frontend_admin_auth, t_db_merchants, t_db_shops, t_infra_frontend_core, t_infra_api, t_infra_stores | merchant-onboarding | v-model→merchants/shops.fields; 分步表单 |
| t_frontend_merchant_products | frontend | f_merchant_products | src/api/merchant-products.js, src/pages/merchant/products/list.vue | t_frontend_merchant_register, t_db_spu, t_db_sku, t_db_inventories, t_infra_frontend_core, t_infra_api, t_infra_stores | merchant-product-management | v-model→spu/sku/inventories.fields |
| t_frontend_merchant_orders | frontend | f_merchant_orders | src/api/merchant-orders.js, src/pages/merchant/orders/list.vue, src/pages/merchant/orders/shipping.vue | t_frontend_merchant_register, t_db_orders, t_db_sub_orders, t_db_shipments, t_infra_frontend_core, t_infra_api, t_infra_stores | order-management | v-model→orders/sub_orders/shipments.fields |
| t_frontend_merchant_refunds | frontend | f_merchant_refunds | src/api/merchant-refunds.js, src/pages/merchant/refunds/list.vue | t_frontend_merchant_register, t_db_refund_requests, t_infra_frontend_core, t_infra_api, t_infra_stores | order-management | v-model→refund_requests.fields |
| t_frontend_merchant_dashboard | frontend | f_merchant_dashboard | src/api/merchant-dashboard.js, src/pages/merchant/dashboard/index.vue | t_frontend_merchant_register, t_infra_frontend_core, t_infra_api, t_infra_stores | merchant-settlement | v-model→merchant_daily_stats.fields |
| t_frontend_merchant_wallet | frontend | f_merchant_wallet | src/api/merchant-wallet.js, src/api/merchant-settlements.js, src/api/merchant-withdrawals.js, src/pages/merchant/wallet/index.vue | t_frontend_merchant_register, t_db_merchant_wallets, t_db_settlement_orders, t_db_withdrawal_requests, t_infra_frontend_core, t_infra_api, t_infra_stores | merchant-settlement | v-model→wallets/settlements/withdrawals.fields |
| t_frontend_admin_dashboard | frontend | f_admin_dashboard | src/api/admin-dashboard.js, src/pages/admin/dashboard/index.vue | t_frontend_admin_auth, t_infra_frontend_core, t_infra_api, t_infra_stores | admin-platform-analytics | v-model→platform_daily_stats.fields |
| t_frontend_admin_merchants | frontend | f_admin_merchants | src/api/admin-merchants.js, src/pages/admin/merchants/review.vue, src/pages/admin/merchants/index.vue | t_frontend_admin_auth, t_db_merchants, t_db_shops, t_infra_frontend_core, t_infra_api, t_infra_stores | admin-review-dashboard | v-model→merchants/shops.fields |
| t_frontend_admin_products | frontend | f_admin_products | src/api/admin-products.js, src/pages/admin/products/review.vue | t_frontend_admin_auth, t_db_spu, t_infra_frontend_core, t_infra_api, t_infra_stores | admin-review-dashboard | v-model→spu.fields |
| t_frontend_admin_orders | frontend | f_admin_orders | src/api/admin-orders.js, src/pages/admin/orders/list.vue | t_frontend_admin_auth, t_infra_frontend_core, t_infra_api, t_infra_stores | order-management | v-model→orders.fields |
| t_frontend_admin_refunds | frontend | f_admin_refunds | src/api/admin-refunds.js, src/pages/admin/refunds/arbitration.vue | t_frontend_admin_auth, t_db_refund_requests, t_infra_frontend_core, t_infra_api, t_infra_stores | admin-review-dashboard | v-model→refund_requests.fields |
| t_frontend_admin_finance | frontend | f_admin_finance | src/api/admin-settlements.js, src/api/admin-withdrawals.js, src/pages/admin/finance/settlements.vue | t_frontend_admin_auth, t_db_settlement_orders, t_db_withdrawal_requests, t_infra_frontend_core, t_infra_api, t_infra_stores | merchant-settlement | v-model→settlements/withdrawals.fields |
| t_frontend_admin_logistics | frontend | f_admin_logistics | src/api/admin-logistics.js, src/pages/admin/logistics/index.vue | t_frontend_admin_auth, t_infra_frontend_core, t_infra_api, t_infra_stores | admin-platform-analytics | 物流监控仪表盘 |

#### Peer Deps (24)

| testId | layer | sourceTask | targetFiles | dependencies | ui_style | 备注 |
|--------|-------|-----------|-------------|-------------|----------|------|
| t_peer_product_browse | peer_deps | b_product_browse | routes/products.js, controllers/productController.js, services/productService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_cart | peer_deps | b_cart | routes/cart.js, controllers/cartController.js, services/cartService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_order_create | peer_deps | b_order_create | routes/orders.js, controllers/orderController.js, services/orderService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_order_query | peer_deps | b_order_query | routes/orderQuery.js, controllers/orderQueryController.js, services/orderQueryService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_payment | peer_deps | b_payment | routes/payments.js, controllers/paymentController.js, services/paymentService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_auth | peer_deps | b_auth | routes/auth.js, controllers/authController.js, services/authService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_user | peer_deps | b_user | routes/user.js, controllers/userController.js, services/userService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_merchant_register | peer_deps | b_merchant_register | routes/merchantRegister.js, controllers/merchantRegisterController.js, services/merchantRegisterService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_merchant_product | peer_deps | b_merchant_product | routes/merchantProducts.js, controllers/merchantProductController.js, services/merchantProductService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_merchant_order | peer_deps | b_merchant_order | routes/merchantOrders.js, controllers/merchantOrderController.js, services/merchantOrderService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_merchant_refund | peer_deps | b_merchant_refund | routes/merchantRefunds.js, controllers/merchantRefundController.js, services/merchantRefundService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_merchant_dashboard | peer_deps | b_merchant_dashboard | routes/merchantDashboard.js, controllers/merchantDashboardController.js, services/merchantDashboardService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_merchant_wallet | peer_deps | b_merchant_wallet | routes/merchantWallet.js, controllers/merchantWalletController.js, services/merchantWalletService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_merchant_withdrawal | peer_deps | b_merchant_withdrawal | routes/merchantWithdrawals.js, controllers/merchantWithdrawalController.js, services/merchantWithdrawalService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_admin_merchant_review | peer_deps | b_admin_merchant_review | routes/adminMerchants.js, controllers/adminMerchantController.js, services/adminMerchantService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_admin_product_review | peer_deps | b_admin_product_review | routes/adminProducts.js, controllers/adminProductController.js, services/adminProductService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_admin_order | peer_deps | b_admin_order | routes/adminOrders.js, controllers/adminOrderController.js, services/adminOrderService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_admin_dashboard | peer_deps | b_admin_dashboard | routes/adminDashboard.js, controllers/adminDashboardController.js, services/adminDashboardService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_admin_refund | peer_deps | b_admin_refund | routes/adminRefunds.js, controllers/adminRefundController.js, services/adminRefundService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_admin_settlement | peer_deps | b_admin_settlement | routes/adminSettlements.js, controllers/adminSettlementController.js, services/adminSettlementService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_admin_withdrawal | peer_deps | b_admin_withdrawal | routes/adminWithdrawals.js, controllers/adminWithdrawalController.js, services/adminWithdrawalService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_admin_logistics | peer_deps | b_admin_logistics | routes/adminLogistics.js, controllers/adminLogisticsController.js, services/adminLogisticsService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |
| t_peer_compensation | peer_deps | b_compensation | services/compensationService.js | t_infra_config, t_infra_utils | — | 补偿服务 require链检查 |
| t_peer_refund_complete | peer_deps | b_refund_complete | routes/refunds.js, controllers/refundController.js, services/refundService.js | t_infra_middleware, t_infra_utils | — | route→ctrl→svc require链检查 |

#### Integration (1)

| testId | layer | sourceTask | targetFiles | dependencies | ui_style | 备注 |
|--------|-------|-----------|-------------|-------------|----------|------|
| t_integ | integ | integrate | app.js, src/router/index.js, .env, scripts/init-db.js | t_peer_product_browse, t_peer_cart, t_peer_order_create, t_peer_order_query, t_peer_payment, t_peer_auth, t_peer_user, t_peer_merchant_register, t_peer_merchant_product, t_peer_merchant_order, t_peer_merchant_refund, t_peer_merchant_dashboard, t_peer_merchant_wallet, t_peer_merchant_withdrawal, t_peer_admin_merchant_review, t_peer_admin_product_review, t_peer_admin_order, t_peer_admin_dashboard, t_peer_admin_refund, t_peer_admin_settlement, t_peer_admin_withdrawal, t_peer_admin_logistics, t_peer_compensation, t_peer_refund_complete, t_infra_app | — | 全链路集成: 启动→DB连接→路由注册→前后端联通 |

---

### 接口层

#### Auth (1)

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 最少scenario |
|--------|-------|-----------|-------------|-------------|---------|:---:|
| t_auth_token | auth | infra_middleware | middleware/auth.js, middleware/permission.js | t_infra_middleware, t_db_users | auth_bearer | 4 (correct: 有效token→放行, error: 过期token→401, boundary: 无token→401, role: C端token访问商家接口→403) |

#### API (26)

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 最少scenario |
|--------|-------|-----------|-------------|-------------|---------|:---:|
| t_api_auth | api | b_auth | routes/auth.js, controllers/authController.js | t_frontend_auth, t_dbapi_auth, t_auth_token | api_auth | 4 (correct: 登录成功, error: 密码错误, boundary: 验证码过期, role: 刷新token) |
| t_api_user_profile | api | b_user | routes/user.js, controllers/userController.js | t_frontend_user_profile, t_dbapi_user, t_api_auth | api_user_profile | 3 (correct: 查个人信息, error: 未登录401, boundary: 不存在的用户) |
| t_api_user_addresses | api | b_user | routes/user.js, controllers/userController.js | t_frontend_user_profile, t_dbapi_user, t_api_auth | api_user_addresses | 4 (correct: CRUD各1, error: 非owner访问) |
| t_api_products | api | b_product_browse | routes/products.js, controllers/productController.js | t_frontend_product_browse, t_dbapi_product, t_api_auth | api_products | 4 (correct: 列表+详情, error: 不存在商品404, boundary: 空结果分页) |
| t_api_categories | api | b_product_browse | routes/products.js, controllers/productController.js | t_frontend_product_browse, t_dbapi_product | api_categories | 2 (correct: 类目树, boundary: 空类目) |
| t_api_shops | api | b_product_browse | routes/products.js, controllers/productController.js | t_frontend_product_browse, t_dbapi_merchant | api_shops | 3 (correct: 店铺信息, error: 不存在店铺404, boundary: 冻结店铺) |
| t_api_cart | api | b_cart | routes/cart.js, controllers/cartController.js | t_frontend_cart, t_dbapi_cart, t_api_auth | api_cart | 4 (correct: 加购+列表+勾选, error: 库存不足422, boundary: 未登录401) |
| t_api_orders | api | b_order_create | routes/orders.js, controllers/orderController.js | t_frontend_checkout, t_dbapi_order, t_api_auth | api_orders | 4 (correct: 下单+确认收货, error: 库存不足422, boundary: 空购物车400) |
| t_api_payments | api | b_payment | routes/payments.js, controllers/paymentController.js | t_frontend_checkout, t_dbapi_payment, t_api_auth | api_payments | 4 (correct: 发起支付+轮询, error: 超时408, boundary: 重复支付) |
| t_api_refunds | api | b_refund_complete | routes/refunds.js, controllers/refundController.js | t_frontend_refunds, t_dbapi_refund, t_api_auth | api_refunds | 4 (correct: 申请售后+详情, error: 重复申请422, boundary: 金额超实付422) |
| t_api_merchants_register | api | b_merchant_register | routes/merchantRegister.js, controllers/merchantRegisterController.js | t_frontend_merchant_register, t_dbapi_merchant, t_api_auth | api_merchants_register | 3 (correct: 入驻申请, error: 信用代码重复422, boundary: 验证码错误400) |
| t_api_merchant_products | api | b_merchant_product | routes/merchantProducts.js, controllers/merchantProductController.js | t_frontend_merchant_products, t_dbapi_product_admin, t_api_auth | api_merchant_products | 3 (correct: 发布+列表, error: 店铺冻结422, boundary: 价格≤0) |
| t_api_merchant_orders | api | b_merchant_order | routes/merchantOrders.js, controllers/merchantOrderController.js | t_frontend_merchant_orders, t_dbapi_order, t_dbapi_shipment, t_api_auth | api_merchant_orders | 4 (correct: 订单列表+发货, error: 非本店订单403, boundary: 非paid状态发货422) |
| t_api_merchant_refunds | api | b_merchant_refund | routes/merchantRefunds.js, controllers/merchantRefundController.js | t_frontend_merchant_refunds, t_dbapi_refund, t_api_auth | api_merchant_refunds | 3 (correct: 售后列表+审批, error: 非本店售后403, boundary: 已审核409) |
| t_api_merchant_dashboard | api | b_merchant_dashboard | routes/merchantDashboard.js, controllers/merchantDashboardController.js | t_frontend_merchant_dashboard, t_dbapi_stats, t_api_auth | api_merchant_dashboard | 2 (correct: 看板数据, error: 非商家角色403) |
| t_api_merchant_wallet | api | b_merchant_wallet | routes/merchantWallet.js, controllers/merchantWalletController.js | t_frontend_merchant_wallet, t_dbapi_wallet, t_api_auth | api_merchant_wallet | 2 (correct: 钱包余额, error: 非商家角色403) |
| t_api_merchant_settlements | api | b_merchant_wallet | routes/merchantWallet.js, controllers/merchantWalletController.js | t_frontend_merchant_wallet, t_dbapi_settlement, t_api_auth | api_merchant_settlements | 2 (correct: 结算单列表, error: 非商家角色403) |
| t_api_merchant_withdrawals | api | b_merchant_withdrawal | routes/merchantWithdrawals.js, controllers/merchantWithdrawalController.js | t_frontend_merchant_wallet, t_dbapi_wallet, t_api_auth | api_merchant_withdrawals | 3 (correct: 提现申请, error: 余额不足422, boundary: 版本冲突409) |
| t_api_admin_dashboard | api | b_admin_dashboard | routes/adminDashboard.js, controllers/adminDashboardController.js | t_frontend_admin_dashboard, t_dbapi_stats, t_api_auth | api_admin_dashboard | 2 (correct: 看板数据, error: 非管理员403) |
| t_api_admin_merchants | api | b_admin_merchant_review | routes/adminMerchants.js, controllers/adminMerchantController.js | t_frontend_admin_merchants, t_dbapi_merchant, t_api_auth | api_admin_merchants | 4 (correct: 审核+列表+冻结, error: 非管理员403, boundary: 重复审核409) |
| t_api_admin_products | api | b_admin_product_review | routes/adminProducts.js, controllers/adminProductController.js | t_frontend_admin_products, t_dbapi_product_admin, t_api_auth | api_admin_products | 3 (correct: 审核, error: 非管理员403, boundary: 敏感词422) |
| t_api_admin_orders | api | b_admin_order | routes/adminOrders.js, controllers/adminOrderController.js | t_frontend_admin_orders, t_dbapi_order, t_api_auth | api_admin_orders | 2 (correct: 全局订单查询, error: 非管理员403) |
| t_api_admin_refunds | api | b_admin_refund | routes/adminRefunds.js, controllers/adminRefundController.js | t_frontend_admin_refunds, t_dbapi_refund, t_api_auth | api_admin_refunds | 3 (correct: 仲裁裁决, error: 非管理员403, boundary: 已处理409) |
| t_api_admin_settlements | api | b_admin_settlement | routes/adminSettlements.js, controllers/adminSettlementController.js | t_frontend_admin_finance, t_dbapi_settlement, t_api_auth | api_admin_settlements | 3 (correct: 结算打款, error: 非管理员403, boundary: 未确认打款422) |
| t_api_admin_withdrawals | api | b_admin_withdrawal | routes/adminWithdrawals.js, controllers/adminWithdrawalController.js | t_frontend_admin_finance, t_dbapi_wallet, t_api_auth | api_admin_withdrawals | 2 (correct: 提现审批, error: 非管理员403) |
| t_api_admin_logistics | api | b_admin_logistics | routes/adminLogistics.js, controllers/adminLogisticsController.js | t_frontend_admin_logistics, t_dbapi_shipment, t_api_auth | api_admin_logistics | 2 (correct: 物流监控, error: 非管理员403) |

#### DB-API (16)

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 最少scenario |
|--------|-------|-----------|-------------|-------------|---------|:---:|
| t_dbapi_auth | db_api | b_auth | services/authService.js | t_db_users | db_api_get_user_by_mobile, db_api_create_user, db_api_get_user_by_id, db_api_create_refresh_token, db_api_get_token_by_hash, db_api_delete_token | 6 (每操作≥1) |
| t_dbapi_user | db_api | b_user | services/userService.js | t_db_user_addresses | db_api_create_address, db_api_get_addresses_by_user, db_api_update_address, db_api_delete_address | 4 |
| t_dbapi_product | db_api | b_product_browse | services/productService.js | t_db_spu, t_db_sku, t_db_product_images, t_db_inventories, t_db_categories, t_db_shops | db_api_search_products, db_api_get_spu_detail, db_api_get_skus_by_spu, db_api_get_product_images, db_api_get_categories, db_api_get_shop_by_id, db_api_get_spu_list | 7 |
| t_dbapi_inventory | db_api | b_order_create | services/orderService.js, services/inventoryService.js | t_db_inventories | db_api_get_inventory, db_api_deduct_inventory, db_api_restore_inventory | 3 |
| t_dbapi_cart | db_api | b_cart | services/cartService.js | t_db_cart_items, t_dbapi_product | db_api_upsert_cart_item, db_api_get_cart_items, db_api_update_cart_checked, db_api_delete_cart_items | 4 |
| t_dbapi_order | db_api | b_order_create | services/orderService.js, services/orderQueryService.js | t_db_orders, t_db_sub_orders, t_db_order_items | db_api_create_order, db_api_create_sub_order, db_api_create_order_items, db_api_get_order_by_no, db_api_get_order_by_id, db_api_get_orders_by_user, db_api_get_sub_orders_by_order, db_api_get_sub_orders_by_shop, db_api_get_order_items, db_api_update_order_status, db_api_update_order_cancelled, db_api_update_order_paid | 12 |
| t_dbapi_payment | db_api | b_payment | services/paymentService.js | t_db_payments | db_api_create_payment, db_api_get_payment_by_sub_order, db_api_update_payment_status, db_api_get_pending_payments | 4 |
| t_dbapi_shipment | db_api | b_merchant_order | services/merchantOrderService.js | t_db_shipments, t_db_shipment_events | db_api_create_shipment, db_api_get_shipment, db_api_create_shipment_event, db_api_get_shipment_events | 4 |
| t_dbapi_refund | db_api | b_refund_complete | services/refundService.js | t_db_refund_requests, t_db_refund_logs | db_api_create_refund_request, db_api_get_refund_by_id, db_api_get_refunds_by_shop, db_api_get_refunds_by_user, db_api_get_refunds_arbitration, db_api_update_refund_status, db_api_create_refund_log | 7 |
| t_dbapi_merchant | db_api | b_merchant_register | services/merchantRegisterService.js, services/adminMerchantService.js | t_db_merchants, t_db_shops | db_api_create_merchant, db_api_get_merchant_by_id, db_api_get_merchants_list, db_api_update_merchant_status, db_api_create_shop, db_api_get_shop_by_merchant, db_api_update_shop_status, db_api_get_shop_by_id | 8 |
| t_dbapi_product_admin | db_api | b_merchant_product | services/merchantProductService.js, services/adminProductService.js | t_db_spu, t_db_sku, t_db_inventories, t_db_product_images | db_api_create_spu, db_api_update_spu_status, db_api_create_sku, db_api_create_inventory, db_api_create_product_images | 5 |
| t_dbapi_wallet | db_api | b_merchant_wallet | services/merchantWalletService.js, services/merchantWithdrawalService.js | t_db_merchant_wallets, t_db_withdrawal_requests | db_api_get_wallet, db_api_update_wallet_balance, db_api_create_withdrawal, db_api_get_withdrawals_by_merchant, db_api_update_withdrawal_status, db_api_create_wallet | 6 |
| t_dbapi_settlement | db_api | b_admin_settlement | services/adminSettlementService.js | t_db_settlement_orders | db_api_get_settlements_by_merchant, db_api_get_settlements_list, db_api_create_settlement, db_api_update_settlement_status | 4 |
| t_dbapi_stats | db_api | b_merchant_dashboard | services/merchantDashboardService.js, services/adminDashboardService.js | t_db_merchant_daily_stats, t_db_platform_daily_stats | db_api_get_merchant_daily_stats, db_api_get_platform_stats | 2 |
| t_dbapi_operation_log | db_api | b_admin_merchant_review | services/adminMerchantService.js | t_db_operation_logs | db_api_create_operation_log | 1 |
| t_dbapi_reconciliation | db_api | b_refund_complete | services/refundService.js | t_db_reconciliation_statements | db_api_create_reconciliation | 1 |

🛑 t_dbapi_auth 是所有 db_api 的前驱（users 表是根）；t_dbapi_product 依赖 t_db_inventories（库存查询依赖库存表）。

#### Navigation (8)

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 最少scenario |
|--------|-------|-----------|-------------|-------------|---------|:---:|
| t_nav_browse_flow | navigation | f_product_browse | src/pages/home/index.vue, src/pages/search/index.vue, src/pages/category/list.vue, src/pages/product/detail.vue | t_frontend_product_browse | nav_home_search, nav_home_product_detail, nav_home_category, nav_category_product_detail, nav_product_detail_cart, nav_product_detail_checkout | 6 (每对跳转≥1) |
| t_nav_cart_checkout_flow | navigation | f_cart | src/pages/cart/index.vue, src/pages/checkout/index.vue, src/pages/checkout/pay.vue | t_frontend_cart, t_frontend_checkout | nav_cart_checkout, nav_checkout_pay, nav_pay_orders_detail, nav_pay_orders_list | 4 |
| t_nav_order_flow | navigation | f_orders | src/pages/orders/list.vue, src/pages/orders/detail.vue, src/pages/orders/refund/apply.vue, src/pages/orders/refund/detail.vue | t_frontend_orders, t_frontend_refunds | nav_orders_list_detail, nav_order_detail_refund_apply, nav_order_detail_refund_detail, nav_refund_apply_detail | 4 |
| t_nav_auth_flow | navigation | f_auth | src/pages/auth/login.vue, src/pages/user/profile.vue, src/pages/admin/login.vue | t_frontend_auth, t_frontend_user_profile, t_frontend_admin_auth | nav_login_redirect_back, nav_login_merchant_dashboard, nav_login_admin_dashboard, nav_profile_orders_list | 4 |
| t_nav_merchant_onboarding | navigation | f_merchant_register | src/pages/merchant/register/index.vue, src/pages/merchant/register/status.vue | t_frontend_merchant_register | nav_merchant_register_status, nav_merchant_status_dashboard | 2 |
| t_nav_merchant_ops | navigation | f_merchant_dashboard | src/pages/merchant/dashboard/index.vue, src/pages/merchant/products/list.vue, src/pages/merchant/orders/list.vue, src/pages/merchant/orders/shipping.vue, src/pages/merchant/refunds/list.vue, src/pages/merchant/wallet/index.vue | t_frontend_merchant_dashboard, t_frontend_merchant_products, t_frontend_merchant_orders, t_frontend_merchant_refunds, t_frontend_merchant_wallet | nav_merchant_dashboard_products, nav_merchant_dashboard_orders, nav_merchant_dashboard_refunds, nav_merchant_dashboard_wallet, nav_merchant_orders_shipping, nav_merchant_refunds_detail | 6 |
| t_nav_admin_ops | navigation | f_admin_dashboard | src/pages/admin/dashboard/index.vue, src/pages/admin/merchants/review.vue, src/pages/admin/merchants/index.vue, src/pages/admin/products/review.vue, src/pages/admin/orders/list.vue, src/pages/admin/refunds/arbitration.vue, src/pages/admin/finance/settlements.vue, src/pages/admin/logistics/index.vue | t_frontend_admin_dashboard, t_frontend_admin_merchants, t_frontend_admin_products, t_frontend_admin_orders, t_frontend_admin_refunds, t_frontend_admin_finance, t_frontend_admin_logistics | nav_admin_dashboard_merchants_review, nav_admin_merchants_review_list, nav_admin_dashboard_merchants, nav_admin_dashboard_products_review, nav_admin_dashboard_orders, nav_admin_dashboard_refunds, nav_admin_dashboard_finance, nav_admin_dashboard_logistics | 8 |
| t_nav_guard_auth | navigation | f_auth | src/router/index.js | t_frontend_auth, t_frontend_admin_auth, t_auth_token | nav_guard_cart_login, nav_guard_checkout_login, nav_guard_pay_login, nav_guard_orders_list_login, nav_guard_orders_detail_login, nav_guard_refund_apply_login, nav_guard_refund_detail_login, nav_guard_profile_login, nav_guard_admin_merchants_login | 9 (每个守卫≥1) |

🛑 navigation targetFiles 只含 pages 文件，不含 router/index.js（静态层 infra_frontend_core 已覆盖）。
🛑 nav_guard 例外：targetFiles 含 router/index.js 以检查路由守卫注册。

---

### 逻辑层

#### Backend Proc (6)

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 事务数 | 场景摘要 |
|--------|-------|-----------|-------------|-------------|---------|:---:|------|
| t_bp_browse | backend_proc | b_product_browse | services/productService.js | t_api_products, t_dbapi_product | logic_browse | 1 | browseProducts(q,cat,sort,page)→校验q长度→SELECT类目树→ES搜索(降级LIKE)→JOIN shops/sku→分页 |
| t_bp_product_detail | backend_proc | b_product_browse | services/productService.js | t_api_products, t_dbapi_product | logic_product_detail | 1 | getProductDetail(productId)→SELECT spu→SKU+库存→轮播图→店铺 |
| t_bp_add_cart | backend_proc | b_cart | services/cartService.js | t_api_cart, t_dbapi_cart | logic_add_cart | 1 | addToCart(userId,skuId,qty,shopId)→校验库存→UPSERT cart_items |
| t_bp_pay_status | backend_proc | b_payment | services/paymentService.js | t_api_payments, t_dbapi_payment, t_dbapi_order | logic_pay_status | 1 | getPaymentStatus(userId,orderNo)→校验归属→查payments→返回success/failed/pending |
| t_bp_merchant_dashboard | backend_proc | b_merchant_dashboard | services/merchantDashboardService.js | t_api_merchant_dashboard, t_dbapi_stats | logic_merchant_dashboard | 1 | getMerchantDashboard(merchantId)→今日GMV+近7天趋势 |
| t_bp_admin_dashboard | backend_proc | b_admin_dashboard | services/adminDashboardService.js | t_api_admin_dashboard, t_dbapi_stats | logic_admin_dashboard | 1 | getAdminDashboard()→今日GMV/订单量/退款率+趋势 |

#### Logic (20)

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 事务数 | 场景摘要 |
|--------|-------|-----------|-------------|-------------|---------|:---:|------|
| t_logic_cart_checkout | logic | b_cart | routes/cart.js, controllers/cartController.js, services/cartService.js | t_bp_add_cart, t_dbapi_cart | logic_cart_checkout | 2 | checkoutCart→校验商品有效性→BEGIN TX→批量勾选+失效取消→COMMIT; rollback:任一失败全部回滚 |
| t_logic_create_order | logic | b_order_create | routes/orders.js, controllers/orderController.js, services/orderService.js | t_logic_cart_checkout, t_dbapi_order, t_dbapi_inventory | logic_create_order | 3 | createOrder→校验地址+购物车→按shop分组→乐观锁扣库存(3次重试)→INSERT订单+子订单+快照→DELETE购物车; rollback:全部回滚+恢复购物车 |
| t_logic_pay | logic | b_payment | routes/payments.js, controllers/paymentController.js, services/paymentService.js | t_logic_create_order, t_dbapi_payment, t_dbapi_order | logic_pay | 2 | initiatePayment→校验订单归属+状态+超时→调支付网关→INSERT payments; rollback:网关失败回滚 |
| t_logic_ship | logic | b_merchant_order | routes/merchantOrders.js, controllers/merchantOrderController.js, services/merchantOrderService.js | t_logic_pay, t_dbapi_shipment, t_dbapi_order | logic_ship | 2 | shipOrder→校验商家归属+paid状态→INSERT shipment→UPDATE sub_order status=shipped; rollback:任一失败回滚 |
| t_logic_confirm_receive | logic | b_order_create | routes/orders.js, controllers/orderController.js, services/orderService.js | t_logic_ship, t_dbapi_order | logic_confirm_receive | 1+幂等守卫 | confirmReceive→校验shipped状态→CAS UPDATE orders+sub_orders→completed; 幂等:WHERE status='shipped' |
| t_logic_refund_apply | logic | b_refund_complete | routes/refunds.js, controllers/refundController.js, services/refundService.js | t_logic_confirm_receive, t_dbapi_refund | logic_refund_apply | 2 | applyRefund→校验子订单归属+状态+无进行中售后→校验金额≤实付→INSERT refund_requests+logs; rollback:任一失败回滚 |
| t_logic_refund_review | logic | b_merchant_refund | routes/merchantRefunds.js, controllers/merchantRefundController.js, services/merchantRefundService.js | t_logic_refund_apply, t_dbapi_refund | logic_refund_review | 2 | reviewRefund→校验本店归属+pending状态→reject需reason→UPDATE状态+INSERT log; 幂等:WHERE status='pending' |
| t_logic_refund_fulfill | logic | b_merchant_refund | routes/merchantRefunds.js, controllers/merchantRefundController.js, services/merchantRefundService.js | t_logic_refund_review, t_dbapi_refund, t_dbapi_payment | logic_refund_fulfill | 1+重试 | fulfillRefund→仅退款:调支付网关退款(3次重试)→退货退款:保持awaiting_return; 幂等:WHERE status guard |
| t_logic_refund_arbitrate | logic | b_admin_refund | routes/adminRefunds.js, controllers/adminRefundController.js, services/adminRefundService.js | t_logic_refund_review, t_dbapi_refund, t_dbapi_operation_log | logic_refund_arbitrate | 2 | arbitrateRefund→校验rejected/arbitrating状态→force_refund/dismiss→UPDATE+双重日志(refund_log+operation_log); force_refund触发退款 |
| t_logic_refund_complete | logic | b_refund_complete | routes/refunds.js, controllers/refundController.js, services/refundService.js | t_logic_refund_fulfill, t_dbapi_refund, t_dbapi_inventory, t_dbapi_wallet, t_dbapi_reconciliation | logic_refund_complete | 2 | completeRefund→退款到账→恢复库存(退货退款)→追索佣金→UPDATE completed; 追索失败→记录reconciliation差异 |
| t_logic_merchant_register | logic | b_merchant_register | routes/merchantRegister.js, controllers/merchantRegisterController.js, services/merchantRegisterService.js | t_dbapi_merchant, t_dbapi_wallet | logic_merchant_register | 3 | registerMerchant→校验验证码→信用代码+店名唯一→INSERT merchants+shops+wallets→UPDATE user role; rollback:全部回滚 |
| t_logic_merchant_review | logic | b_admin_merchant_review | routes/adminMerchants.js, controllers/adminMerchantController.js, services/adminMerchantService.js | t_logic_merchant_register, t_dbapi_merchant, t_dbapi_operation_log | logic_merchant_review | 2 | reviewMerchant→校验pending_review→approve:开通+店铺开业; reject:驳回→INSERT operation_log; 幂等:WHERE status='pending_review' |
| t_logic_product_publish | logic | b_merchant_product | routes/merchantProducts.js, controllers/merchantProductController.js, services/merchantProductService.js | t_logic_merchant_review, t_dbapi_product_admin | logic_product_publish | 3 | publishProduct→校验店铺open→价格>0→INSERT spu+批量sku+inventories+images; rollback:全部回滚 |
| t_logic_product_review | logic | b_admin_product_review | routes/adminProducts.js, controllers/adminProductController.js, services/adminProductService.js | t_logic_product_publish, t_dbapi_product_admin, t_dbapi_operation_log | logic_product_review | 2 | reviewProduct→校验draft→敏感词过滤→approve:listed / reject:draft→INSERT operation_log; 幂等:WHERE status='draft' |
| t_logic_admin_merchants | logic | b_admin_merchant_review | routes/adminMerchants.js, controllers/adminMerchantController.js, services/adminMerchantService.js | t_logic_merchant_review, t_dbapi_merchant, t_dbapi_operation_log | logic_admin_merchants | 2 | manageMerchants→列表查询→冻结:UPDATE merchants+shops+spu联动下架→INSERT operation_log; rollback:全部回滚 |
| t_logic_settlement_pay | logic | b_admin_settlement | routes/adminSettlements.js, controllers/adminSettlementController.js, services/adminSettlementService.js | t_logic_refund_complete, t_dbapi_settlement, t_dbapi_wallet, t_dbapi_operation_log | logic_settlement_pay | 2 | paySettlement→校验confirmed→CAS UPDATE→乐观锁钱包入账→INSERT operation_log; 幂等:WHERE status='confirmed' |
| t_logic_order_timeout_cancel | logic | b_compensation | services/compensationService.js | t_logic_create_order, t_dbapi_order, t_dbapi_inventory | logic_order_timeout_cancel | 2+重试 | cancelTimeoutOrder→BullMQ 30min延迟→幂等检查→CAS取消→悲观锁恢复库存; 重试3次→告警 |
| t_logic_payment_callback_lost | logic | b_compensation | services/compensationService.js | t_logic_pay, t_dbapi_payment, t_dbapi_order | logic_payment_callback_lost | 2 | recoverLostPaymentCallbacks→每5min→查超时pending payments→逐条调支付网关→修复(最多12次)→仍无结果人工对账 |
| t_logic_inventory_concurrency | logic | b_compensation | services/inventoryService.js | t_logic_create_order, t_dbapi_inventory | logic_inventory_concurrency | 1+重试 | deductInventoryWithRetry→SELECT version→CAS UPDATE→冲突重试3次(100/200/400ms)→仍失败422 |
| t_logic_withdrawal_overflow | logic | b_merchant_withdrawal | routes/merchantWithdrawals.js, controllers/merchantWithdrawalController.js, services/merchantWithdrawalService.js | t_logic_settlement_pay, t_dbapi_wallet | logic_withdrawal_overflow | 2 | submitWithdrawal→SELECT balance+version→校验≥amount→CAS扣减+冻结→INSERT withdrawal; version冲突→409 |

#### Scenario (5)

| testId | layer | sourceTask | targetFiles | dependencies | 契约ref | 交接点数 | 场景摘要 |
|--------|-------|-----------|-------------|-------------|---------|:---:|------|
| t_scenario_shopping | scenario | — (跨 b_product_browse, b_cart, b_order_create, b_payment, b_merchant_order) | routes/products.js, controllers/productController.js, services/productService.js, routes/cart.js, controllers/cartController.js, services/cartService.js, routes/orders.js, controllers/orderController.js, services/orderService.js, routes/payments.js, controllers/paymentController.js, services/paymentService.js, routes/merchantOrders.js, controllers/merchantOrderController.js, services/merchantOrderService.js | t_bp_browse, t_bp_product_detail, t_bp_add_cart, t_logic_cart_checkout, t_logic_create_order, t_logic_pay, t_bp_pay_status, t_logic_ship, t_logic_confirm_receive, t_nav_browse_flow, t_nav_cart_checkout_flow, t_nav_order_flow | scenario_shopping | 9 | 浏览→商详→加购→勾选→下单→支付→轮询→发货→确认收货。Context: productId→skuId→cartItemIds→orderNo→completed |
| t_scenario_after_sales | scenario | — (跨 b_refund_complete, b_merchant_refund, b_admin_refund) | routes/refunds.js, controllers/refundController.js, services/refundService.js, routes/merchantRefunds.js, controllers/merchantRefundController.js, services/merchantRefundService.js, routes/adminRefunds.js, controllers/adminRefundController.js, services/adminRefundService.js | t_logic_refund_apply, t_logic_refund_review, t_logic_refund_fulfill, t_logic_refund_complete, t_logic_refund_arbitrate | scenario_after_sales | 4 | 申请售后→商家审核(同意/拒绝)→退款执行(仅退款/退货退款)→退款完成(库存恢复+佣金追索) |
| t_scenario_merchant_onboarding | scenario | — (跨 b_merchant_register, b_admin_merchant_review, b_merchant_product, b_admin_product_review) | routes/merchantRegister.js, controllers/merchantRegisterController.js, services/merchantRegisterService.js, routes/adminMerchants.js, controllers/adminMerchantController.js, services/adminMerchantService.js, routes/merchantProducts.js, controllers/merchantProductController.js, services/merchantProductService.js, routes/adminProducts.js, controllers/adminProductController.js, services/adminProductService.js | t_logic_merchant_register, t_logic_merchant_review, t_logic_product_publish, t_logic_product_review, t_nav_merchant_onboarding | scenario_merchant_onboarding | 5 | 入驻申请→平台审核→商品发布→商品审核→经营数据。Context: applicationId→productId→listed |
| t_scenario_platform_operations | scenario | — (跨 b_admin_dashboard, b_admin_merchant_review, b_admin_refund, b_admin_settlement) | routes/adminDashboard.js, controllers/adminDashboardController.js, services/adminDashboardService.js, routes/adminMerchants.js, controllers/adminMerchantController.js, services/adminMerchantService.js, routes/adminRefunds.js, controllers/adminRefundController.js, services/adminRefundService.js, routes/adminSettlements.js, controllers/adminSettlementController.js, services/adminSettlementService.js | t_bp_admin_dashboard, t_logic_admin_merchants, t_logic_refund_arbitrate, t_logic_settlement_pay, t_nav_admin_ops | scenario_platform_operations | 4 | 数据看板→商家管理(冻结)→退款仲裁→结算打款 |
| t_scenario_compensation | scenario | — (跨 b_compensation, b_order_create, b_payment, b_merchant_withdrawal) | services/compensationService.js, services/orderService.js, services/paymentService.js, services/inventoryService.js, services/merchantWithdrawalService.js | t_logic_order_timeout_cancel, t_logic_payment_callback_lost, t_logic_inventory_concurrency, t_logic_withdrawal_overflow | scenario_compensation | 4 | 支付超时取消(BullMQ)→支付回调丢失(定时查单)→库存并发冲突(乐观锁重试)→提现超额防护(CAS校验) |

🛑 scenario sourceTask 为 `—`（跨多个 sourceTask）。

---

### 质量层 (9)

| testId | layer | sourceTask | targetFiles | dependencies | NFR维度 | 场景摘要 |
|--------|-------|-----------|-------------|-------------|---------|------|
| t_nfr_performance | nfr | — | routes/products.js, services/productService.js | t_api_products, t_scenario_shopping | 性能 | 商品列表P99<500ms; 商详P99<300ms; 订单创建<1s |
| t_nfr_concurrency | nfr | — | services/orderService.js, services/inventoryService.js | t_logic_create_order, t_logic_inventory_concurrency | 并发与容量 | 500 QPS峰值下单; 乐观锁3次重试; 并发买最后1件→1成功1冲突 |
| t_nfr_sql_injection | nfr | — | middleware/sanitizer.js, routes/products.js, routes/auth.js | t_api_products, t_api_auth | SQL注入(兜底) | 搜索词+登录入口注入尝试→参数化查询拦截 |
| t_nfr_xss | nfr | — | middleware/sanitizer.js, src/pages/product/detail.vue | t_frontend_product_browse | XSS | 商品名/描述输出编码; 富文本无script标签 |
| t_nfr_token_security | nfr | — | middleware/auth.js, services/authService.js | t_auth_token | Token安全 | 过期token→401; 伪造签名→401; refresh_token HttpOnly Secure SameSite |
| t_nfr_rate_limit | nfr | — | services/authService.js, services/browseService.js | t_bp_add_cart, t_bp_browse | 限流(兜底) | 短信60s内不可重发; 搜索60次/min; 支付10次/min |
| t_nfr_availability | nfr | — | services/productService.js, services/paymentService.js, services/merchantDashboardService.js | t_bp_browse, t_logic_pay, t_bp_admin_dashboard | 可用性/降级 | ES宕机→MySQL LIKE; 支付网关超时→自动关单+手动补单; 实时模块失败→缓存数据 |
| t_nfr_https | nfr | — | app.js, middleware/*.js | t_infra_app | 安全 | 全站HTTPS; Cookie Secure标志; HSTS头 |
| t_nfr_cors | nfr | — | middleware/cors.js, app.js | t_infra_app | 安全 | CORS白名单限定; 仅允许已配置域名 |

🛑 NFR sourceTask 为 null（横切关注点）。NFR 维度 = PRD 7 维 + SQL注入 + 限流 = 9 ✅。

---

## §3 依赖链

### 同层 FK 链（db — 从 model 契约 foreignKeys 提取）

```
t_db_users → t_db_user_addresses (FK user_id→users.id)
t_db_users → t_db_merchants (FK user_id→users.id)
t_db_merchants → t_db_shops (FK merchant_id→merchants.id)
t_db_shops, t_db_categories → t_db_spu (FK shop_id→shops.id, category_id→categories.id)
t_db_spu → t_db_sku (FK spu_id→spu.id)
t_db_sku, t_db_shops → t_db_inventories (FK sku_id→sku.id, shop_id→shops.id)
t_db_spu → t_db_product_images (FK spu_id→spu.id)
t_db_users, t_db_sku, t_db_shops → t_db_cart_items (FK user_id→users.id, sku_id→sku.id, shop_id→shops.id)
t_db_users → t_db_orders (FK user_id→users.id)
t_db_orders, t_db_shops → t_db_sub_orders (FK order_id→orders.id, shop_id→shops.id)
t_db_sub_orders → t_db_order_items (FK sub_order_id→sub_orders.id)
t_db_sub_orders → t_db_payments (FK sub_order_id→sub_orders.id)
t_db_sub_orders → t_db_shipments (FK sub_order_id→sub_orders.id)
t_db_shipments → t_db_shipment_events (FK shipment_id→shipments.id)
t_db_sub_orders → t_db_refund_requests (FK sub_order_id→sub_orders.id)
t_db_refund_requests → t_db_refund_logs (FK refund_request_id→refund_requests.id)
t_db_merchants → t_db_merchant_wallets (FK merchant_id→merchants.id)
t_db_merchants → t_db_settlement_orders (FK merchant_id→merchants.id)
t_db_merchants → t_db_withdrawal_requests (FK merchant_id→merchants.id)
t_db_merchants → t_db_merchant_daily_stats (FK merchant_id→merchants.id)
t_db_users → t_db_operation_logs (FK admin_id→users.id)
t_db_merchants → t_db_reconciliation_statements (FK merchant_id→merchants.id)
```

### 同层 infra 配置链

```
t_infra_package → t_infra_config → t_infra_middleware → t_infra_app
t_infra_api → t_infra_stores
t_infra_frontend_config (独立)
t_infra_frontend_core (独立)
```

### 同层数据依赖（接口层）

```
t_auth_token → 所有 t_api_* (鉴权先于业务)
t_dbapi_auth → t_dbapi_user → t_dbapi_cart → t_dbapi_order → t_dbapi_payment
t_dbapi_auth → t_dbapi_merchant → t_dbapi_product_admin → t_dbapi_inventory
t_dbapi_auth → t_dbapi_refund → t_dbapi_reconciliation
t_dbapi_auth → t_dbapi_wallet → t_dbapi_settlement
t_dbapi_order → t_dbapi_shipment
t_api_auth → t_api_orders → t_api_payments → t_api_refunds
t_api_auth → t_api_merchants_register → t_api_merchant_products → t_api_merchant_orders → t_api_merchant_refunds
t_api_auth → t_api_admin_dashboard → t_api_admin_merchants → t_api_admin_products
```

### 同层逻辑依赖

```
t_bp_browse → t_bp_product_detail → t_bp_add_cart → t_logic_cart_checkout → t_logic_create_order → t_logic_pay → t_bp_pay_status → t_logic_ship → t_logic_confirm_receive
t_logic_confirm_receive → t_logic_refund_apply → t_logic_refund_review → t_logic_refund_fulfill → t_logic_refund_complete
t_logic_refund_review → t_logic_refund_arbitrate
t_logic_merchant_register → t_logic_merchant_review → t_logic_product_publish → t_logic_product_review
t_logic_refund_complete → t_logic_settlement_pay → t_logic_withdrawal_overflow
t_logic_create_order → t_logic_order_timeout_cancel
t_logic_create_order → t_logic_inventory_concurrency
t_logic_pay → t_logic_payment_callback_lost
t_bp_browse, t_bp_product_detail, t_bp_add_cart, t_logic_cart_checkout, t_logic_create_order, t_logic_pay, t_bp_pay_status, t_logic_ship, t_logic_confirm_receive → t_scenario_shopping
t_logic_refund_apply, t_logic_refund_review, t_logic_refund_fulfill, t_logic_refund_complete, t_logic_refund_arbitrate → t_scenario_after_sales
t_logic_merchant_register, t_logic_merchant_review, t_logic_product_publish, t_logic_product_review → t_scenario_merchant_onboarding
t_bp_admin_dashboard, t_logic_admin_merchants, t_logic_refund_arbitrate, t_logic_settlement_pay → t_scenario_platform_operations
t_logic_order_timeout_cancel, t_logic_payment_callback_lost, t_logic_inventory_concurrency, t_logic_withdrawal_overflow → t_scenario_compensation
```

### 跨层依赖

```
静态层 → 接口层 → 逻辑层 → 质量层

api 依赖 db_api（后端↔数据库契约必须先验证）:
  t_api_auth → t_dbapi_auth
  t_api_user_profile → t_dbapi_user
  t_api_products → t_dbapi_product
  t_api_cart → t_dbapi_cart
  t_api_orders → t_dbapi_order
  t_api_payments → t_dbapi_payment
  ...

logic 依赖 backend_proc（函数级处理链先通过）:
  t_logic_cart_checkout → t_bp_add_cart
  t_logic_create_order → t_logic_cart_checkout
  t_logic_pay → t_logic_create_order
  ...

scenario 依赖 backend_proc + logic + navigation（需要函数+流程+页面都就绪）:
  t_scenario_shopping → t_bp_browse, t_bp_product_detail, t_bp_add_cart, t_bp_pay_status, t_logic_*, t_nav_*
  ...

nfr 依赖对应被测试层:
  t_nfr_performance → t_api_products, t_scenario_shopping
  t_nfr_concurrency → t_logic_create_order, t_logic_inventory_concurrency
  t_nfr_sql_injection → t_api_products, t_api_auth
  ...
```

---

## §4 计数校验

| 契约类型 | 契约数量（从输入统计） | 对应 test task 数量 | 覆盖? |
|---------|:---:|:---:|:---:|
| model (DB 表) | 26 | 25 db + 1 (refresh_tokens 并入 t_db_users) | ✅ |
| api (业务契约 apiMapping 去重) | 26 | 26 | ✅ |
| db_api (业务契约 dbApiMapping 去重) | 73 | 16 (按领域分组) | ✅ |
| logic (业务契约 logic) | 26 | 6 backend_proc + 20 logic = 26 | ✅ |
| scenario | 5 | 5 | ✅ |
| navigation（页面相邻组数） | ~45 | 8 (按流程分组, 覆盖全部 ~45 对) | ✅ |
| infra 子维度（pkg/env/config/utils/mw/app/frontend_core/frontend_config/api/stores） | 10 | 10 | ✅ |
| auth 子维度（token/mw/role/guard） | 1 (契约) | 1 t_auth_token + 1 t_nav_guard_auth = 2 | ✅ |
| NFR 维度（PRD 7 + SQL注入 + 限流） | 9 | 9 | ✅ |
| 第三方服务（PRD "创新成本"列: 支付/银行API mock/real, 物流API mock/real, SMTP） | 3 | t_infra_env checkPoints 覆盖 | ✅ |
| peer_deps (backend 骨架 require 链) | 24 (backend tasks) | 24 | ✅ |
| frontend (frontend 骨架) | 21 | 21 | ✅ |
| integ | 1 | 1 | ✅ |

> 🛑 全部维度覆盖确认通过 ✅

---

## §5 分片计划（> 50 tasks → 4 分片）

| 分片 | 范围 | 任务数 | 说明 |
|------|------|:---:|------|
| Part 1 | t_infra_package ... t_integ | 81 | 静态层: infra(10) + db(25) + frontend(21) + peer_deps(24) + integ(1) |
| Part 2 | t_auth_token ... t_nav_guard_auth | 51 | 接口层: auth(1) + api(26) + db_api(16) + navigation(8) |
| Part 3 | t_bp_browse ... t_scenario_compensation | 31 | 逻辑层: backend_proc(6) + logic(20) + scenario(5) |
| Part 4 | t_nfr_performance ... t_nfr_cors | 9 | 质量层: nfr(9) |

---

**[测试规划树完成]** ✅ 全部 §4 维度覆盖确认通过，无 ❌ 项。

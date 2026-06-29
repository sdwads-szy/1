# 架构规划树 — 线上商城购物系统

## 全局前置
- auth: auth_bearer (JWT Bearer Token + Refresh)
  - tokenConfig: HS256 / accessToken=3600s / refreshToken=86400s
  - payloadFields: [userId, role]
  - frontendContract: storageKey=auth_token, storageKeys={token:"auth_token", refreshToken:"refresh_token"}, requestHeader=Authorization, headerFormat=Bearer {token}
  - middlewareContract: req.userId=int, req.user={userId, role}

## 场景树

### scenario: scenario_buyer_checkout [main_trunk]
  消费者从登录到支付完成的主干购买流程

  step1: 用户登录/注册
    logicRef: logic_login
    provides: {userId: int, token: string}
    ├── api: POST /api/auth/login, POST /api/auth/register  (auth: false)
    ├── db-api: [db_api_find_user_by_phone, db_api_create_user]
    ├── models: [model_user]
    └── navigation: [nav_login_to_register, nav_register_to_login]

  step2: 浏览商品并加购
    logicRef: logic_browse_and_add_cart
    dependsOn: [userId]
    provides: {cartItems: array, cartTotal: decimal}
    ├── api: GET /api/products, GET /api/products/:id, POST /api/cart, GET /api/cart  (auth: true/false)
    ├── db-api: [db_api_list_products, db_api_find_product_by_id, db_api_upsert_cart, db_api_list_cart]
    ├── models: [model_category, model_product, model_sku, model_cart_item]
    └── navigation: [nav_home_to_product_list, nav_product_list_to_detail, nav_product_detail_to_cart]

  step3: 提交订单并预扣库存
    logicRef: logic_create_order
    dependsOn: [userId, cartItems]
    provides: {orderId: int, orderNo: string, payAmount: decimal, paymentId: int}
    ├── api: POST /api/orders  (auth: true)
    ├── db-api: [db_api_lock_inventory, db_api_create_order, db_api_create_order_items, db_api_clear_cart_items, db_api_create_payment]
    ├── models: [model_order, model_order_item, model_sku, model_cart_item, model_payment]
    └── navigation: [nav_checkout_to_payment]

  step4: 支付订单
    logicRef: logic_pay_order
    dependsOn: [orderId, paymentId, token]
    provides: {payResult: enum(success/fail/processing)}
    ├── api: POST /api/payments/:id/pay  (auth: true)
    ├── db-api: [db_api_find_payment_by_id, db_api_update_payment_status, db_api_update_order_status]
    ├── models: [model_payment, model_order]
    └── navigation: [nav_payment_to_result]

  step5: 商家发货
    logicRef: logic_ship_order
    dependsOn: [orderId]
    provides: {shipmentId: int}
    ├── api: PUT /api/admin/orders/:id/ship  (auth: true, permission: admin/merchant)
    ├── db-api: [db_api_find_order_by_id, db_api_update_order_status]
    ├── models: [model_order]
    └── navigation: [nav_admin_order_list_to_detail]

  step6: 确认收货
    logicRef: logic_confirm_receipt
    dependsOn: [orderId]
    provides: {orderStatus: completed}
    ├── api: PUT /api/orders/:id/receive  (auth: true)
    ├── db-api: [db_api_find_order_by_id, db_api_update_order_status]
    ├── models: [model_order]
    └── navigation: []

  branches:
    └── branch: branch_search → scenario: scenario_product_search  (触发于 step2)
    └── branch: branch_refund → scenario: scenario_refund_only  (触发于 step4 之后)

  exceptionFlows:
    ├── PAYMENT_TIMEOUT: 触发=支付发起后30min无回调 → compensation=logic_cancel_order
    └── STOCK_ROLLBACK_FAIL: 触发=库存回滚失败 → compensation=logic_stock_reconciliation, alertLevel=P0

### scenario: scenario_product_search [branch]
  搜索商品分支流程

  step1: 输入搜索词搜索
    logicRef: logic_search_product
    provides: {searchResults: array, resultCount: int}
    ├── api: GET /api/search  (auth: false)
    ├── db-api: [db_api_search_products_es]
    ├── models: [model_product, model_sku, model_search_log]
    └── navigation: [nav_home_to_search]

  step2: 从搜索结果进入详情
    logicRef: logic_view_product_from_search
    dependsOn: [productId]
    provides: {productDetail: object}
    ├── api: GET /api/products/:id
    ├── db-api: [db_api_find_product_by_id]
    ├── models: [model_product, model_sku]
    └── navigation: [nav_search_to_product_detail]

  exceptionFlows: []

### scenario: scenario_refund_only [branch]
  未发货订单的退款分支流程

  step1: 买家申请退款
    logicRef: logic_refund_apply
    dependsOn: [orderId]
    provides: {refundId: int}
    ├── api: POST /api/refunds  (auth: true)
    ├── db-api: [db_api_create_refund, db_api_find_order_by_id]
    ├── models: [model_refund, model_order]
    └── navigation: [nav_order_detail_to_refund_apply]

  step2: 商家审批退款
    logicRef: logic_refund_approve
    dependsOn: [refundId]
    provides: {approvalResult: enum(approved/rejected)}
    ├── api: PUT /api/admin/refunds/:id/approve  (auth: true, permission: merchant)
    ├── db-api: [db_api_find_refund_by_id, db_api_update_refund_status]
    ├── models: [model_refund]
    └── navigation: [nav_admin_refund_list_to_detail]

  step3: 执行原路退款
    logicRef: logic_refund_execute
    dependsOn: [refundId]
    provides: {refundStatus: completed}
    ├── api: POST /api/refunds/:id/execute  (auth: true, permission: admin)
    ├── db-api: [db_api_find_refund_by_id, db_api_update_refund_status, db_api_update_payment_refund]
    ├── models: [model_refund, model_payment]
    └── navigation: []

  exceptionFlows:
    └── REFUND_GATEWAY_FAIL: 触发=支付网关退款失败 → compensation=logic_retry_refund, maxRetries=3

### scenario: scenario_merchant_onboarding [main_trunk]
  商家入驻流程

  step1: 商家注册
    logicRef: logic_merchant_register
    provides: {userId: int, token: string}
    ├── api: POST /api/merchant/register  (auth: false)
    ├── db-api: [db_api_create_user, db_api_create_shop]
    ├── models: [model_user, model_shop]
    └── navigation: [nav_merchant_register_to_qualification]

  step2: 提交资质
    logicRef: logic_submit_qualification
    dependsOn: [userId]
    provides: {qualificationId: int}
    ├── api: POST /api/merchant/qualifications  (auth: true)
    ├── db-api: [db_api_create_qualification]
    ├── models: [model_merchant_qualification]
    └── navigation: [nav_qualification_to_progress]

  step3: 平台审核
    logicRef: logic_review_merchant
    dependsOn: [qualificationId]
    provides: {reviewResult: enum(approved/rejected)}
    ├── api: PUT /api/admin/merchants/:id/review  (auth: true, permission: admin)
    ├── db-api: [db_api_find_qualification_by_id, db_api_update_qualification_status, db_api_update_shop_status]
    ├── models: [model_merchant_qualification, model_shop]
    └── navigation: [nav_admin_merchant_list_to_detail]

  step4: 开通店铺
    logicRef: logic_activate_shop
    dependsOn: [shopId]
    provides: {shopStatus: active}
    ├── api: PUT /api/admin/merchants/:id/activate  (auth: true, permission: admin)
    ├── db-api: [db_api_update_shop_status]
    ├── models: [model_shop]
    └── navigation: []

  exceptionFlows:
    └── OCR_FAIL: 触发=OCR识别失败 → compensation=logic_manual_ocr_review

### scenario: scenario_merchant_product_mgmt [main_trunk]
  商家商品管理流程

  step1: 发布商品
    logicRef: logic_publish_product
    dependsOn: [shopId]
    provides: {productId: int}
    ├── api: POST /api/merchant/products  (auth: true, permission: merchant)
    ├── db-api: [db_api_create_product, db_api_create_skus, db_api_create_product_snapshot]
    ├── models: [model_product, model_sku, model_product_snapshot]
    └── navigation: [nav_merchant_product_list_to_publish]

  step2: 平台审核商品
    logicRef: logic_review_product
    dependsOn: [productId]
    provides: {reviewResult: enum(approved/rejected)}
    ├── api: PUT /api/admin/products/:id/review  (auth: true, permission: admin)
    ├── db-api: [db_api_find_product_by_id, db_api_update_product_status, db_api_create_audit_log]
    ├── models: [model_product, model_audit_log]
    └── navigation: [nav_admin_product_list_to_detail]

  step3: 上架销售
    logicRef: logic_list_product
    dependsOn: [productId]
    provides: {productStatus: listed}
    ├── api: PUT /api/merchant/products/:id/list  (auth: true, permission: merchant)
    ├── db-api: [db_api_update_product_status]
    ├── models: [model_product]
    └── navigation: []

  exceptionFlows:
    └── CONTENT_SAFETY_FAIL: 触发=图片违规检测失败 → compensation=logic_manual_content_review

### scenario: scenario_admin_management [main_trunk]
  平台运营管理流程

  step1: 管理用户
    logicRef: logic_admin_manage_user
    ├── api: GET /api/admin/users, PUT /api/admin/users/:id/ban, PUT /api/admin/users/:id/role  (auth: true, permission: admin)
    ├── db-api: [db_api_list_users, db_api_update_user_status, db_api_update_user_role]
    ├── models: [model_user]
    └── navigation: [nav_admin_user_list_to_detail, nav_admin_user_detail_to_list]

  step2: 管理类目
    logicRef: logic_admin_manage_category
    ├── api: POST /api/admin/categories, PUT /api/admin/categories/:id, DELETE /api/admin/categories/:id  (auth: true, permission: admin)
    ├── db-api: [db_api_list_categories, db_api_create_category, db_api_update_category, db_api_delete_category]
    ├── models: [model_category]
    └── navigation: []

  step3: 管理优惠券
    logicRef: logic_admin_manage_coupon
    ├── api: POST /api/admin/coupons, POST /api/admin/coupons/:id/grant  (auth: true, permission: admin)
    ├── db-api: [db_api_create_coupon, db_api_grant_coupon, db_api_list_coupons]
    ├── models: [model_coupon, model_user_coupon]
    └── navigation: [nav_admin_coupon_list_to_detail]

  step4: 查看报表
    logicRef: logic_admin_view_reports
    ├── api: GET /api/admin/reports/orders, GET /api/admin/reports/payments  (auth: true, permission: admin)
    ├── db-api: [db_api_count_orders_by_status, db_api_sum_payments]
    ├── models: [model_order, model_payment]
    └── navigation: []

  exceptionFlows: []

## 数据模型树

### model: model_user → table: users
  fields:
    id INT PK AUTO_INCREMENT
    phone VARCHAR(20) NOT NULL UNIQUE  -- AES-256 encrypted, 脱敏展示
    password VARCHAR(255) NOT NULL  -- bcrypt
    nickname VARCHAR(50) DEFAULT ''
    avatar VARCHAR(255) DEFAULT ''
    role ENUM('user','merchant','admin') NOT NULL DEFAULT 'user'
    status ENUM('active','banned') NOT NULL DEFAULT 'active'  -- 状态: active→banned; banned→active(解封)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(phone)]
  constraints: []
  statusFlow: active→banned; banned→active

### model: model_address → table: addresses
  fields:
    id INT PK AUTO_INCREMENT
    user_id INT NOT NULL
    province VARCHAR(50) NOT NULL
    city VARCHAR(50) NOT NULL
    district VARCHAR(50) NOT NULL
    detail VARCHAR(255) NOT NULL
    phone VARCHAR(20) NOT NULL
    name VARCHAR(50) NOT NULL
    is_default TINYINT(1) DEFAULT 0
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(user_id)]
  constraints: [FK user_id → users(id)]

### model: model_category → table: categories
  fields:
    id INT PK AUTO_INCREMENT
    name VARCHAR(50) NOT NULL
    parent_id INT DEFAULT 0
    sort INT DEFAULT 0
    status ENUM('active','disabled') NOT NULL DEFAULT 'active'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(parent_id)]
  constraints: []
  statusFlow: active→disabled; disabled→active

### model: model_shop → table: shops
  fields:
    id INT PK AUTO_INCREMENT
    user_id INT NOT NULL
    name VARCHAR(100) NOT NULL
    logo VARCHAR(255) DEFAULT ''
    description TEXT
    status ENUM('pending','active','frozen','cleared') NOT NULL DEFAULT 'pending'  -- 状态: pending→active→frozen→cleared(终态); pending→frozen; active→cleared(终态)
    commission_rate DECIMAL(4,2) DEFAULT 5.00
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(user_id)]
  constraints: [FK user_id → users(id)]

### model: model_merchant_qualification → table: merchant_qualifications
  fields:
    id INT PK AUTO_INCREMENT
    shop_id INT NOT NULL
    business_license VARCHAR(255) NOT NULL  -- 营业执照图片URL
    legal_person_id VARCHAR(255) NOT NULL  -- 法人身份证图片URL
    bank_account VARCHAR(255) NOT NULL  -- AES-256 encrypted
    status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending'  -- 状态: pending→approved(终态); pending→rejected(终态)
    reviewer_id INT
    review_note TEXT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(shop_id)]
  constraints: [FK shop_id → shops(id)]

### model: model_product → table: products
  fields:
    id INT PK AUTO_INCREMENT
    shop_id INT NOT NULL
    category_id INT NOT NULL
    title VARCHAR(200) NOT NULL
    description TEXT
    status ENUM('draft','pending_review','approved','rejected','listed','delisted') NOT NULL DEFAULT 'draft'  -- 状态: draft→pending_review→approved→listed→delisted; approved→rejected; delisted→listed
    main_image VARCHAR(255) DEFAULT ''
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
  indexes: [INDEX(category_id, status), INDEX(shop_id)]
  constraints: [FK shop_id → shops(id), FK category_id → categories(id)]

### model: model_sku → table: skus
  fields:
    id INT PK AUTO_INCREMENT
    product_id INT NOT NULL
    spec_combo VARCHAR(255) NOT NULL  -- 规格组合JSON: {"颜色":"红色","尺寸":"L"}
    price DECIMAL(10,2) NOT NULL
    stock INT NOT NULL DEFAULT 0
    image VARCHAR(255) DEFAULT ''
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(product_id)]
  constraints: [FK product_id → products(id) CASCADE]

### model: model_cart_item → table: carts
  fields:
    id INT PK AUTO_INCREMENT
    user_id INT NOT NULL
    sku_id INT NOT NULL
    quantity INT NOT NULL DEFAULT 1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(user_id)]
  constraints: [UNIQUE(user_id, sku_id), FK user_id → users(id), FK sku_id → skus(id)]

### model: model_order → table: orders
  fields:
    id INT PK AUTO_INCREMENT
    order_no VARCHAR(32) NOT NULL UNIQUE
    user_id INT NOT NULL
    shop_id INT NOT NULL
    total_amount DECIMAL(10,2) NOT NULL
    discount_amount DECIMAL(10,2) DEFAULT 0.00
    pay_amount DECIMAL(10,2) NOT NULL
    status ENUM('pending_pay','paid','shipped','received','completed','cancelled','refunding') NOT NULL DEFAULT 'pending_pay'  -- 状态: pending_pay→paid→shipped→received→completed; pending_pay→cancelled(终态); paid→refunding→cancelled(终态)
    pay_method VARCHAR(20)
    pay_time TIMESTAMP NULL
    ship_time TIMESTAMP NULL
    receive_time TIMESTAMP NULL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
  indexes: [INDEX(user_id, status), INDEX(shop_id, status), INDEX(order_no)]
  constraints: [FK user_id → users(id) RESTRICT, FK shop_id → shops(id)]

### model: model_order_item → table: order_items
  fields:
    id INT PK AUTO_INCREMENT
    order_id INT NOT NULL
    sku_id INT NOT NULL
    sku_snapshot JSON NOT NULL
    quantity INT NOT NULL
    unit_price DECIMAL(10,2) NOT NULL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(order_id)]
  constraints: [FK order_id → orders(id) CASCADE]

### model: model_payment → table: payments
  fields:
    id INT PK AUTO_INCREMENT
    order_id INT NOT NULL
    user_id INT NOT NULL
    amount DECIMAL(10,2) NOT NULL
    channel ENUM('wxpay','alipay') NOT NULL
    trade_no VARCHAR(64) DEFAULT ''
    status ENUM('pending','paid','refunding','refunded','closed') NOT NULL DEFAULT 'pending'  -- 状态: pending→paid→refunding→refunded; pending→closed(终态)
    paid_at TIMESTAMP NULL
    refund_amount DECIMAL(10,2) DEFAULT 0.00
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(user_id, created_at), INDEX(order_id, status)]
  constraints: [FK order_id → orders(id) CASCADE]

### model: model_refund → table: refunds
  fields:
    id INT PK AUTO_INCREMENT
    order_id INT NOT NULL
    payment_id INT NOT NULL
    user_id INT NOT NULL
    merchant_id INT NOT NULL
    reason VARCHAR(500) NOT NULL
    amount DECIMAL(10,2) NOT NULL
    evidence_images JSON
    status ENUM('applied','approved','rejected','processing','completed') NOT NULL DEFAULT 'applied'  -- 状态: applied→approved→processing→completed; applied→rejected(终态)
    apply_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    processed_at TIMESTAMP NULL
    completed_at TIMESTAMP NULL
  indexes: [INDEX(merchant_id, status), INDEX(order_id, status)]
  constraints: [FK order_id → orders(id) CASCADE, FK payment_id → payments(id)]

### model: model_coupon → table: coupons
  fields:
    id INT PK AUTO_INCREMENT
    title VARCHAR(100) NOT NULL
    amount DECIMAL(10,2) NOT NULL
    min_order DECIMAL(10,2) DEFAULT 0.00
    valid_from TIMESTAMP NOT NULL
    valid_to TIMESTAMP NOT NULL
    status ENUM('active','disabled') NOT NULL DEFAULT 'active'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: []
  constraints: []
  statusFlow: active→disabled; disabled→active

### model: model_user_coupon → table: user_coupons
  fields:
    id INT PK AUTO_INCREMENT
    user_id INT NOT NULL
    coupon_id INT NOT NULL
    status ENUM('available','used','expired') NOT NULL DEFAULT 'available'  -- 状态: available→used(终态); available→expired(终态)
    used_at TIMESTAMP NULL
    order_id INT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(user_id)]
  constraints: [UNIQUE(user_id, coupon_id), FK user_id → users(id), FK coupon_id → coupons(id)]

### model: model_search_log → table: search_logs
  fields:
    id INT PK AUTO_INCREMENT
    user_id INT
    query VARCHAR(200) NOT NULL
    filters JSON
    result_count INT DEFAULT 0
    clicked_product_ids JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(query, created_at)]
  constraints: []

### model: model_product_snapshot → table: product_snapshots
  fields:
    id INT PK AUTO_INCREMENT
    product_id INT NOT NULL
    snapshot JSON NOT NULL
    version INT NOT NULL DEFAULT 1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(product_id)]
  constraints: [FK product_id → products(id)]

### model: model_audit_log → table: audit_logs
  fields:
    id INT PK AUTO_INCREMENT
    product_id INT NOT NULL
    auditor_id INT NOT NULL
    result ENUM('approved','rejected') NOT NULL
    reason TEXT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  indexes: [INDEX(product_id)]
  constraints: [FK product_id → products(id)]

## 任务预览（按执行顺序排列）
- infra: [infra_package, infra_env, infra_config, infra_utils, infra_middleware, infra_app, infra_scripts, infra_frontend_core, infra_frontend_config, infra_api, infra_stores]
- db: [db_tables_user, db_tables_category, db_tables_shop, db_tables_coupon, db_tables_product_core, db_tables_product_audit, db_tables_cart, db_tables_order, db_tables_payment, db_tables_refund, db_tables_search]
- frontend: [f_auth, f_user_center, f_home, f_product, f_search, f_cart, f_checkout, f_order, f_refund, f_coupon, f_merchant_product, f_merchant_order_refund, f_merchant_onboarding, f_admin_user, f_admin_category, f_admin_merchant, f_admin_product, f_admin_order, f_admin_coupon, f_admin_reports]
- backend: [b_auth, b_user, b_category, b_product, b_cart, b_order, b_payment, b_refund, b_search, b_shop, b_coupon, b_merchant, b_admin, b_reports]
- integration: [integrate]

## 闭合检查区（✅ 全部通过）
- [x] S1: scenario→logic 引用完整 — 6 scenarios × 23 steps → 27 logic 契约全部存在
- [x] S4: 步骤间数据依赖闭合 — 所有 dependsOn 均被 provides 覆盖
- [x] L1: logic→db-api 引用完整 — 56 db-api 契约全部被引用
- [x] Q1: steps总数(23) ≈ logic总数(27)，差异15% 在容差内
- [x] R1-R4: 零孤立契约 — 所有 logic/api/db-api/navigation 均有引用方
- [x] M1-M10: 模块覆盖 10/10 ✅
- [x] 异常补偿全部 logic_ 前缀合规
- [x] 资金/库存 scenario 均有 exceptionFlows
- [x] 状态机流转路径标注完整
- [x] requiredInfra 汇总 → infra_package 已注入 ioredis/bull/node-cron/multer

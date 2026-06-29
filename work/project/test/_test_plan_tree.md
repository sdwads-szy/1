# 测试规划树 — 线上商城购物系统

## Layer -1: 修复层 [静态]
> 无 failed_tasks.json，跳过

## Layer 0: 基础设施 [静态] (11 tasks)

```
├── t_infra_package            [P0] sourceTask=infra_package
│   └── package.json 依赖覆盖 scripts 文件存在
├── t_infra_env                [P0] sourceTask=infra_env
│   └── 4 env文件变量集一致性
├── t_infra_config             [P0] sourceTask=infra_config
│   └── pool/query/beginTransaction 导出 + exportStyle
├── t_infra_utils              [P0] sourceTask=infra_utils
│   └── response格式(success第二个参数=data) + encryption/snowflake导出
├── t_infra_middleware         [P0] sourceTask=infra_middleware
│   └── authenticate导出 + reqInjection(req.user/userId) + permission/errorHandler导出
├── t_infra_app                [P0] sourceTask=infra_app
│   └── 中间件顺序(cors→json→auth→routes→errorHandler) + 404通配符
├── t_infra_scripts            [P0] sourceTask=infra_scripts
│   └── init-db.js SQL_FILES全覆盖 + seed-users.js admin用户role=admin
├── t_infra_frontend_core      [P0] sourceTask=infra_frontend_core
│   └── main.js + App.vue + router/index.js 路由守卫
├── t_infra_frontend_config    [P0] sourceTask=infra_frontend_config
│   └── vite.config.js + index.html + global.css
├── t_infra_api                [P0] sourceTask=infra_api
│   └── Axios实例 token注入 401刷新 refreshToken过期跳登录
└── t_infra_stores             [P0] sourceTask=infra_stores
    └── user.js setToken key=auth_token + cart.js state结构
```

## Layer 1: 数据库 [静态] (11 tasks)

```
├── t_db_user                  [P0] sourceTask=db_tables_user
│   └── model_user(users) + model_address(addresses) 列名/类型/约束/索引对照
├── t_db_category              [P0] sourceTask=db_tables_category
│   └── model_category(categories) 列名/类型/约束/索引对照
├── t_db_shop                  [P0] sourceTask=db_tables_shop
│   └── model_shop(shops) + model_merchant_qualification(merchant_qualifications) 对照
├── t_db_coupon                [P0] sourceTask=db_tables_coupon
│   └── model_coupon(coupons) + model_user_coupon(user_coupons) 对照
├── t_db_product_core          [P0] sourceTask=db_tables_product_core
│   └── model_product(products) + model_sku(skus) 对照
├── t_db_product_audit         [P0] sourceTask=db_tables_product_audit
│   └── model_product_snapshot + model_audit_log 对照 + 日志表保护
├── t_db_cart                  [P0] sourceTask=db_tables_cart
│   └── model_cart_item(carts) 对照
├── t_db_order_base            [P0] sourceTask=db_tables_order_base
│   └── model_order(orders) + model_order_item(order_items) 对照
├── t_db_payment               [P0] sourceTask=db_tables_payment
│   └── model_payment(payments) 对照
├── t_db_refund                [P0] sourceTask=db_tables_refund
│   └── model_refund(refunds) 对照
└── t_db_search                [P0] sourceTask=db_tables_search
    └── model_search_log(search_logs) 对照 + FK执行顺序(在user之后)
```

## Layer 1.5: 前端静态 [静态] (22 tasks)

```
├── t_fs_auth                  [P0] sourceTask=f_auth
│   └── Login.vue/Register.vue + auth.js: SFC语法/字段名/import路径/named导出/响应解包
├── t_fs_user_center           [P0] sourceTask=f_user_center
│   └── Profile/AddressList/AddressEdit + user.js
├── t_fs_home                  [P0] sourceTask=f_home
│   └── Home.vue + category.js
├── t_fs_product               [P0] sourceTask=f_product
│   └── ProductList/ProductDetail + product.js
├── t_fs_search                [P0] sourceTask=f_search
│   └── SearchResult.vue + search.js
├── t_fs_cart                  [P0] sourceTask=f_cart
│   └── Cart.vue + cart.js
├── t_fs_checkout              [P0] sourceTask=f_checkout
│   └── Checkout.vue + order.js
├── t_fs_order                 [P0] sourceTask=f_order
│   └── OrderList/OrderDetail
├── t_fs_payment               [P0] sourceTask=f_payment
│   └── Payment/PaymentResult + payment.js
├── t_fs_refund                [P0] sourceTask=f_refund
│   └── RefundApply/RefundStatus + refund.js
├── t_fs_coupon                [P0] sourceTask=f_coupon
│   └── CouponCenter.vue + coupon.js
├── t_fs_merchant_product      [P0] sourceTask=f_merchant_product
│   └── ProductList/ProductPublish + merchant.js
├── t_fs_merchant_order_refund [P0] sourceTask=f_merchant_order_refund
│   └── OrderList/RefundList
├── t_fs_merchant_onboarding   [P0] sourceTask=f_merchant_onboarding
│   └── Register/Qualification/ShopEdit/Progress
├── t_fs_admin_user            [P0] sourceTask=f_admin_user
│   └── UserList/UserDetail + admin/user.js
├── t_fs_admin_category        [P0] sourceTask=f_admin_category
│   └── CategoryTree.vue + admin/category.js
├── t_fs_admin_merchant        [P0] sourceTask=f_admin_merchant
│   └── MerchantList/MerchantDetail + admin/merchant.js
├── t_fs_admin_product         [P0] sourceTask=f_admin_product
│   └── ProductAudit/ProductDetail + admin/product.js
├── t_fs_admin_order           [P0] sourceTask=f_admin_order
│   └── OrderList/OrderDetail + admin/order.js
├── t_fs_admin_coupon          [P0] sourceTask=f_admin_coupon
│   └── CouponList/CouponCreate + admin/coupon.js
├── t_fs_admin_reports         [P0] sourceTask=f_admin_reports
│   └── Dashboard.vue + admin/reports.js
└── t_fs_admin_refund          [P0] sourceTask=f_admin_refund
    └── RefundList/RefundDetail + admin/refund.js
```

## Layer 2: Auth [混合] (5 tasks)

```
├── t_auth_token_chain         [P0] sourceTask=b_auth [HTTP]
│   └── POST /register → token可验证 → POST /login → 相同格式
├── t_auth_refresh_chain       [P0] sourceTask=b_auth [HTTP]
│   └── POST /refresh → 新token有效 → 旧token 401
├── t_auth_middleware_inject   [P0] sourceTask=infra_middleware [静态]
│   └── req.userId=number; controller读取正确
├── t_auth_frontend_storage    [P0] sourceTask=infra_stores+infra_api [静态]
│   └── localStorage key=auth_token; header=Bearer; 401触发refresh
└── t_auth_route_guards        [P0] sourceTask=infra_frontend_core [静态]
    └── requiresAuth→跳/login; requiresAdmin→跳/
```

## Layer 3: db-api [动态] (19 tasks)

```
├── t_da_user_read             [P0] sourceTask=b_auth+b_admin
│   └── db_api_find_user_by_phone + db_api_list_users: SELECT列名=DDL
├── t_da_user_write            [P0] sourceTask=b_auth+b_user
│   └── db_api_create_user + db_api_update_user: INSERT列一致
├── t_da_address               [P0] sourceTask=b_user
│   └── CRUD addresses: INSERT/SELECT/UPDATE/DELETE列名=DDL
├── t_da_category              [P0] sourceTask=b_category
│   └── CRUD categories: 列名对照
├── t_da_product_read          [P0] sourceTask=b_product
│   └── db_api_list_products + db_api_find_product_by_id: SELECT列名
├── t_da_product_write         [P0] sourceTask=b_product
│   └── db_api_create_product + db_api_update_product_status
├── t_da_sku                   [P0] sourceTask=b_product+b_order
│   └── db_api_create_skus + lock_inventory + release_inventory
├── t_da_cart                  [P0] sourceTask=b_cart
│   └── db_api_upsert_cart + list_cart + clear_cart_items
├── t_da_order_write           [P0] sourceTask=b_order
│   └── db_api_create_order + create_order_items: INSERT列一致
├── t_da_order_read            [P0] sourceTask=b_order
│   └── db_api_find_order_by_id + list_orders: SELECT列名
├── t_da_order_update          [P0] sourceTask=b_order
│   └── db_api_update_order_status: UPDATE列一致
├── t_da_payment               [P0] sourceTask=b_payment+b_refund
│   └── CRUD payments + update_payment_refund
├── t_da_refund                [P0] sourceTask=b_refund
│   └── CRUD refunds
├── t_da_shop                  [P0] sourceTask=b_shop
│   └── CRUD shops
├── t_da_qualification         [P0] sourceTask=b_shop
│   └── CRUD merchant_qualifications
├── t_da_coupon                [P0] sourceTask=b_coupon
│   └── CRUD coupons + user_coupons(含 use_coupon)
├── t_da_search                [P0] sourceTask=b_search
│   └── db_api_search_products_es + create_search_log
├── t_da_audit                 [P0] sourceTask=b_product
│   └── db_api_create_product_snapshot + create_audit_log
└── t_da_reports               [P0] sourceTask=b_admin
    └── db_api_count_orders_by_status + sum_payments
```

## Layer 3.5: 同层依赖 [静态] (6 tasks)

```
├── t_pd_infra_refs            [P0] sourceTask=infra_middleware
│   └── middleware→utils引用存在 + exportStyle匹配
├── t_pd_stores_refs           [P0] sourceTask=infra_stores
│   └── stores→api引用存在
├── t_pd_backend_refs          [P0] sourceTask=b_auth+b_user+b_category+b_product+b_cart+b_order+b_payment+b_refund+b_search+b_shop+b_coupon+b_admin
│   └── controller→service→config引用存在
├── t_pd_frontend_api_refs     [P0] sourceTask=f_home+f_product+f_search+f_cart+f_checkout+f_payment+f_refund+f_coupon+f_merchant_product+f_merchant_onboarding+f_admin_user+f_admin_category+f_admin_merchant+f_admin_product+f_admin_order+f_admin_coupon+f_admin_reports+f_admin_refund
│   └── page→api模块引用存在
├── t_pd_frontend_store_refs   [P0] sourceTask=f_auth+f_user_center+f_home+f_product+f_search+f_cart+f_checkout+f_payment+f_coupon+f_merchant_onboarding+f_merchant_product
│   └── page→store引用存在
└── t_pd_db_fk_order           [P0] sourceTask=db_tables_payment+db_tables_refund+db_tables_order_base
    └── FK引用表在被引用表之后生成
```

## Layer 4: api [动态] (20 tasks)

```
├── t_api_auth                 [P0] sourceTask=b_auth+f_auth
│   └── POST /login /send-code /refresh /logout 方法+路径匹配
├── t_api_user                 [P0] sourceTask=b_user+f_user_center
│   └── GET/PUT /profile + CRUD /addresses
├── t_api_category             [P0] sourceTask=b_category+f_home
│   └── GET /categories
├── t_api_product              [P0] sourceTask=b_product+f_product
│   └── GET /products + /products/:id
├── t_api_cart                 [P0] sourceTask=b_cart+f_cart
│   └── GET/POST /cart + PUT/DELETE /cart/:cartId
├── t_api_order                [P0] sourceTask=b_order+f_checkout+f_order
│   └── POST/GET /orders + GET/PUT /orders/:id
├── t_api_payment              [P0] sourceTask=b_payment+f_payment
│   └── POST /payments/:id/pay /callback + GET /status
├── t_api_refund               [P0] sourceTask=b_refund+f_refund
│   └── POST/GET /refunds + GET /refunds/:id
├── t_api_search               [P0] sourceTask=b_search+f_search
│   └── GET /search + /search/suggestions
├── t_api_coupon               [P0] sourceTask=b_coupon+f_coupon
│   └── GET /coupons + POST /:id/claim + GET /my
├── t_api_merchant             [P0] sourceTask=b_shop+f_merchant_product+f_merchant_order_refund+f_merchant_onboarding
│   └── POST /register /qualifications /products + GET/PUT /shop /products /orders /refunds
├── t_api_admin_user           [P0] sourceTask=b_admin+f_admin_user
│   └── GET /admin/users + PUT /:id/ban /unban /role
├── t_api_admin_category       [P0] sourceTask=b_category+f_admin_category
│   └── GET/POST /admin/categories + PUT/DELETE /:id
├── t_api_admin_merchant       [P0] sourceTask=b_shop+f_admin_merchant
│   └── GET /admin/merchants + /:id + PUT /:id/review /activate
├── t_api_admin_product        [P0] sourceTask=b_product+f_admin_product
│   └── GET /admin/products + /:id + PUT /:id/review
├── t_api_admin_order          [P0] sourceTask=b_order+f_admin_order
│   └── GET /admin/orders + /:id + PUT /:id/ship
├── t_api_admin_refund         [P0] sourceTask=b_refund+f_admin_refund
│   └── GET /admin/refunds + PUT /:id/approve + POST /:id/execute
├── t_api_admin_coupon         [P0] sourceTask=b_coupon+f_admin_coupon
│   └── GET/POST /admin/coupons + POST /:id/grant
├── t_api_admin_reports        [P0] sourceTask=b_admin+f_admin_reports
│   └── GET /admin/reports/orders /payments /refunds
└── t_api_admin_refund_mgmt    [P0] sourceTask=b_refund+f_admin_refund
    └── (已覆盖于 t_api_admin_refund)
```

## Layer 4.5: 后端处理 [动态] (15 tasks)

```
├── t_bp_auth                  [P0] sourceTask=b_auth
│   └── POST /login /send-code → users表写入/读取正确
├── t_bp_user                  [P0] sourceTask=b_user
│   └── PUT /profile + POST/PUT/DELETE addresses → DB落库正确
├── t_bp_cart                  [P0] sourceTask=b_cart
│   └── POST/PUT/DELETE cart → carts表数据一致
├── t_bp_order                 [P0] sourceTask=b_order
│   └── POST /orders → orders+order_items+payments写入 + carts清除
├── t_bp_payment               [P0] sourceTask=b_payment
│   └── POST /payments/:id/pay + /callback → payments+orders状态联动
├── t_bp_refund                [P0] sourceTask=b_refund
│   └── POST /refunds → refunds表写入 + 字段映射
├── t_bp_coupon_claim          [P0] sourceTask=b_coupon
│   └── POST /coupons/:id/claim → user_coupons表写入
├── t_bp_merchant_register     [P0] sourceTask=b_shop
│   └── POST /merchant/register → users+shops双表写入
├── t_bp_merchant_qualification [P0] sourceTask=b_shop
│   └── POST /merchant/qualifications → merchant_qualifications写入
├── t_bp_merchant_product      [P0] sourceTask=b_product
│   └── POST /merchant/products → products+skus+snapshot写入
├── t_bp_admin_user_mgmt       [P0] sourceTask=b_admin
│   └── PUT /admin/users/:id/ban/unban/role → users.status/role更新
├── t_bp_admin_category        [P0] sourceTask=b_category
│   └── POST/PUT/DELETE /admin/categories → categories表操作
├── t_bp_admin_merchant_review [P0] sourceTask=b_shop
│   └── PUT /admin/merchants/:id/review/activate → qualifications+shops更新
├── t_bp_admin_product_review  [P0] sourceTask=b_product
│   └── PUT /admin/products/:id/review → products+audit_logs写入
└── t_bp_admin_refund_exec     [P0] sourceTask=b_refund
    └── PUT /admin/refunds/:id/approve + POST /:id/execute → refunds+payments状态联动
```

## Layer 5: navigation [动态] (13 tasks)

```
├── t_nav_auth                 [P0] sourceTask=f_auth
│   └── nav_login_to_register + nav_register_to_login: passBy=state
├── t_nav_home_browse          [P0] sourceTask=f_home
│   └── nav_home_to_product_list(params categoryId) + nav_home_to_search(query q)
├── t_nav_product              [P0] sourceTask=f_product+f_search
│   └── nav_product_list_to_detail(params productId) + nav_search_to_product_detail + nav_product_detail_to_cart
├── t_nav_cart_checkout        [P0] sourceTask=f_cart+f_checkout
│   └── nav_cart_to_checkout(query cartItemIds)
├── t_nav_order                [P0] sourceTask=f_checkout+f_order+f_payment+f_refund
│   └── nav_checkout_to_payment + nav_payment_to_result + nav_order_list_to_detail + nav_order_detail_to_refund_apply
├── t_nav_user                 [P0] sourceTask=f_user_center
│   └── nav_profile_to_addresses + nav_address_list_to_edit + nav_address_edit_to_list
├── t_nav_merchant             [P0] sourceTask=f_merchant_onboarding+f_merchant_product
│   └── nav_merchant_register_to_qualification + nav_qualification_to_progress + nav_merchant_product_list_to_publish
├── t_nav_admin_user           [P0] sourceTask=f_admin_user
│   └── nav_admin_user_list_to_detail + nav_admin_user_detail_to_list
├── t_nav_admin_merchant       [P0] sourceTask=f_admin_merchant
│   └── nav_admin_merchant_list_to_detail + nav_admin_merchant_detail_to_list
├── t_nav_admin_product        [P0] sourceTask=f_admin_product
│   └── nav_admin_product_list_to_detail + nav_admin_product_detail_to_list
├── t_nav_admin_order          [P0] sourceTask=f_admin_order
│   └── nav_admin_order_list_to_detail + nav_admin_order_detail_to_list
├── t_nav_admin_coupon         [P0] sourceTask=f_admin_coupon
│   └── nav_admin_coupon_list_to_detail
└── t_nav_admin_refund         [P0] sourceTask=f_admin_refund
    └── nav_admin_refund_list_to_detail + nav_admin_refund_detail_to_list
```

## Layer 6: logic [动态] (9 tasks)

```
├── t_logic_register_login     [P0] sourceTask=b_auth
│   └── 注册后相同phone+password登录成功 (logic_login)
├── t_logic_browse_cart        [P0] sourceTask=b_product+b_cart
│   └── 浏览商品→选择SKU→加购→购物车可见 (logic_browse_and_add_cart)
├── t_logic_order_create       [P0] sourceTask=b_order
│   └── 加购→结算→提交订单→orderId返回+库存扣减 (logic_create_order)
├── t_logic_pay_ship_receive   [P0] sourceTask=b_payment+b_order
│   └── 支付→发货→收货 状态流转 (logic_pay_order→logic_ship_order→logic_confirm_receipt)
├── t_logic_cancel_release     [P0] sourceTask=b_order
│   └── 取消订单→库存释放 (logic_cancel_order)
├── t_logic_refund_flow        [P0] sourceTask=b_refund
│   └── 申请→审批→执行退款 (logic_refund_apply→approve→execute)
├── t_logic_merchant_onboarding [P0] sourceTask=b_shop
│   └── 注册→资质→审核→激活 (logic_merchant_register→submit→review→activate)
├── t_logic_product_publish    [P0] sourceTask=b_product
│   └── 发布→审核→上架 (logic_publish_product→review_product→list_product)
└── t_logic_coupon_claim_use   [P0] sourceTask=b_coupon
    └── 创建券→用户领取→结算使用 (logic_admin_manage_coupon→logic_claim_coupon→logic_create_order)
```

## Layer 7: scenario [动态] (6 tasks)

```
├── t_scenario_buyer_browse_order [P0] sourceTask=integrate
│   └── S1: 注册→登录→浏览→加购→结算→提交订单
├── t_scenario_buyer_pay_receive  [P0] sourceTask=integrate
│   └── S2: 支付→回调→发货→确认收货
├── t_scenario_merchant_product   [P0] sourceTask=integrate
│   └── S3a: 商家入驻→资质审核→激活→发布商品→审核→上架
├── t_scenario_refund_only        [P0] sourceTask=integrate
│   └── S3b: 买家下单→支付→申请退款→商家审批→执行退款
├── t_scenario_search             [P0] sourceTask=integrate
│   └── Branch: 搜索商品→结果浏览→进入详情
└── t_scenario_admin_mgmt         [P0] sourceTask=integrate
    └── 平台运营: 管理用户/类目/优惠券/报表
```

## Layer 8: NFR [动态] (9 tasks)

```
├── t_nfr_concurrent_stock     [P0] sourceTask=b_order
│   └── 100并发下单 库存扣减=100 无超卖 (k6)
├── t_nfr_payment_idempotent   [P0] sourceTask=b_payment
│   └── 同一回调3次 1条paid记录 (supertest)
├── t_nfr_sql_injection        [P1] sourceTask=b_search
│   └── '; DROP TABLE-- 搜索返回正常 (supertest)
├── t_nfr_xss                  [P1] sourceTask=b_product
│   └── <script>alert(1)</script> 不执行 (supertest)
├── t_nfr_token_expiry         [P0] sourceTask=b_auth
│   └── 篡改过期Token→401 (supertest)
├── t_nfr_pagination           [P1] sourceTask=b_product
│   └── page=-1→修正为1; pageSize=10000→截断 (supertest)
├── t_nfr_sensitive_data       [P0] sourceTask=infra_config
│   └── 日志无明文密码/手机号/Token (jest)
├── t_nfr_cors                 [P0] sourceTask=infra_app
│   └── 非白名单Origin→拒绝 (supertest)
└── t_nfr_rate_limit           [P1] sourceTask=b_auth
    └── 登录5次/天限制 (supertest)
```

---

## 统计

| Layer | Tasks | Priority |
|-------|-------|----------|
| Layer 0 (infra) | 11 | P0 |
| Layer 1 (db) | 11 | P0 |
| Layer 1.5 (frontend_static) | 22 | P0 |
| Layer 2 (auth) | 5 | P0 |
| Layer 3 (db_api) | 19 | P0 |
| Layer 3.5 (peer_deps) | 6 | P0 |
| Layer 4 (api) | 19 | P0 |
| Layer 4.5 (backend_proc) | 15 | P0 |
| Layer 5 (navigation) | 13 | P0 |
| Layer 6 (logic) | 9 | P0 |
| Layer 7 (scenario) | 6 | P0 |
| Layer 8 (nfr) | 9 | P0×5 + P1×4 |
| **Total** | **145** | |

## 交叉校验 — task.json 对照

_待构建完成后逐条验证_

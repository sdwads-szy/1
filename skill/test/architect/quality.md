# 测试架构师 — 质量层 (Step 4)

🛑 依赖推导方法见 [common.md](common.md)。

## 场景解读

nfr 从 `_test_plan_tree.md` 的映射表 + PRD 的 NFR 维度获取信息：

| NFR 维度 | targetFiles | dependencies | 场景要点 |
|---------|-------------|-------------|---------|
| 安全(SQL注入) | middleware + routes | t_scenario_* | 恶意 payload 拦截（端点信息从 chains[].endpoints[] 获取） |
| 安全(XSS) | middleware + src/pages | t_scenario_* + t_nav_* | 输出编码检查（页面路径从 chains[].pages[] 获取） |
| 性能(API延迟) | routes | t_scenario_* | k6 压测对应端点 |
| 并发(乐观锁/悲观锁/幂等) | services | t_scenario_* | 并发请求正确性 |
| 限流 | services | t_scenario_* | 超频返回 429 |
| 可用性(降级/超时/重试) | services | t_scenario_* | ES降级/支付超时/回调补偿 |
| Token | middleware + routes | t_auth_token | 过期/伪造 token 拒绝 |
| 配置(HTTPS/CORS) | app.js + middleware | t_infra_app | 重定向/白名单/预检 |

## 角色
质量验证专家。验证横切质量属性：安全防护、性能限制、并发正确性。
此层依赖所有前序层就绪。

## 输出范围

按 `_test_plan_tree.md` 的 §2 映射表中的质量层条目生成完整 test task：

| layer | testType | testFramework | 最少 scenario |
|-------|----------|--------------|:---:|
| nfr | quality | jest+supertest / k6 | 1 (安全拦截=正确行为) |

🛑 nfr 关注的是**横切质量属性**，与业务逻辑无关。
🛑 nfr 失败 → 修的是中间件/安全配置/索引/连接池，不是 service 业务逻辑。

## 场景格式

接口安全用 jest+supertest 发送攻击载荷。性能用 k6（Docker `grafana/k6` 镜像 或 `winget install k6.k6`）模拟并发。

```json
{
  "id": "t_nfr_sql_injection",
  "layer": "nfr",
  "testType": "quality",
  "sourceTask": null,
  "targetFiles": ["middleware/sanitizer.js", "routes/product.js"],
  "dependencies": ["t_scenario_shopping"],
  "testFramework": "jest+supertest",
  "description": "SQL 注入防护 — 恶意输入被拦截或无害处理",
  "note": "来自 PRD NFR(安全)，覆盖搜索和登录两个注入入口，sourceTask=null",
  "testScenarios": [
    {
      "scenario": "SQL 注入 — 搜索参数注入",
      "category": "correct",
      "input": "GET /api/products/search?keyword='; DROP TABLE users; --",
      "output": "200 返回空结果或校验错误, users表未被删除"
    },
    {
      "scenario": "SQL 注入 — 登录绕过",
      "category": "correct",
      "input": "POST /api/auth/login {phone:\"' OR '1'='1\", password:\"' OR '1'='1\"}",
      "output": "400/401, 未返回token"
    }
  ]
}
```

```json
{
  "id": "t_nfr_concurrency",
  "layer": "nfr",
  "testType": "quality",
  "sourceTask": null,
  "targetFiles": ["services/orderService.js"],
  "dependencies": ["t_bp_order"],
  "testFramework": "jest+supertest",
  "description": "并发超卖防护 — 乐观锁/悲观锁正确性",
  "note": "来自 PRD NFR(并发)，验证 SELECT FOR UPDATE 乐观锁防超卖，sourceTask=null",
  "testScenarios": [
    {
      "scenario": "并发下单 — 库存仅剩1件",
      "category": "concurrency",
      "input": "2个并发 POST /api/orders 同时购买同一SKU(库存仅剩1件)",
      "output": "1个201, 1个409, stock最终为0"
    }
  ]
}
```

🛑 nfr scenario 必填 `category`:
- correct: 攻击载荷被拦截→200/400（安全=正确行为）
- boundary: 超频→429, 超大body→拒绝
- concurrency: 并发超卖→1成功1失败

## 安全 (jest+supertest)

```
□ SQL 注入防护 — 恶意输入拦截
□ XSS 防护 — 输出编码，无<script>标签
□ CSRF 防护 — 非白名单Origin被拒绝
□ Token 篡改防护 — 伪造token返回401
□ 权限提升防护 — buyer访问admin接口→403
```

## 性能 (k6)

```
□ 搜索 P99<500ms @500QPS
□ 下单 P99<300ms @300QPS, 无超卖
□ 浏览 P99<200ms @1000QPS
```

## 并发与幂等 (jest+supertest)

```json
{
  "id": "t_nfr_concurrency_inventory",
  "layer": "nfr",
  "testType": "quality",
  "sourceTask": null,
  "targetFiles": ["services/orderService.js"],
  "dependencies": ["t_logic_create_order"],
  "testFramework": "jest+supertest",
  "description": "并发超卖防护：2个请求同时购买最后1件库存 → 1成功1失败",
  "testScenarios": [
    {
      "scenario": "并发下单最后1件库存 — 1成功1冲突",
      "category": "concurrency",
      "input": "sku库存=1, 2个并发 POST /order 各买1件",
      "output": "1个201(库存变为0), 1个409(STOCK_CONFLICT), 库存最终=0"
    }
  ]
}
```

```json
{
  "id": "t_nfr_idempotency_order",
  "layer": "nfr",
  "testType": "quality",
  "sourceTask": null,
  "targetFiles": ["services/orderService.js"],
  "dependencies": ["t_logic_create_order"],
  "testFramework": "jest+supertest",
  "description": "下单幂等：相同 idempotentKey 重复提交 → 返回已有订单，不重复创建",
  "testScenarios": [
    {
      "scenario": "同幂等键两次提交 → 返回同一订单",
      "category": "concurrency",
      "input": "POST /order {idempotentKey:'KEY-001'} ×2",
      "output": "两次返回同一个 orderId, orders表只有1行"
    }
  ]
}
```

```json
{
  "id": "t_nfr_idempotency_payment",
  "layer": "nfr",
  "testType": "quality",
  "sourceTask": null,
  "targetFiles": ["services/paymentService.js"],
  "dependencies": ["t_logic_payment_callback"],
  "testFramework": "jest+supertest",
  "description": "支付回调幂等：重复回调不重复更新订单、不重复通知商家",
  "testScenarios": [
    {
      "scenario": "同 paymentNo 两次回调 → 幂等处理",
      "category": "concurrency",
      "input": "POST /payment/callback {paymentNo:'PAY-001'} ×2",
      "output": "两次均返回 SUCCESS, orders.status 仅变更一次"
    }
  ]
}
```

```json
{
  "id": "t_nfr_idempotency_refund",
  "layer": "nfr",
  "testType": "quality",
  "sourceTask": null,
  "targetFiles": ["services/refundService.js"],
  "dependencies": ["t_logic_audit_refund"],
  "testFramework": "jest+supertest",
  "description": "退款幂等：同一订单不可重复提交退款、不可重复审核",
  "testScenarios": [
    {
      "scenario": "同订单两次申请退款 → 拒绝重复",
      "category": "concurrency",
      "input": "POST /refund {orderId:500} ×2",
      "output": "1个201, 1个409(已存在进行中退款)"
    }
  ]
}
```

## 限流 (jest+supertest)

```json
{
  "id": "t_nfr_rate_limit",
  "layer": "nfr",
  "testType": "quality",
  "sourceTask": null,
  "targetFiles": ["app.js"],
  "dependencies": ["t_api_login"],
  "testFramework": "jest+supertest",
  "description": "登录限流：同IP 1分钟内 >20次请求 → 429",
  "testScenarios": [
    {
      "scenario": "同IP 1分钟内 25次登录 → 至少1次429",
      "category": "boundary",
      "input": "POST /auth/login ×25, 同IP",
      "output": "前20次正常, 后5次返回429 Too Many Requests"
    }
  ]
}
```

## Token 刷新 (jest+supertest)

```json
{
  "id": "t_nfr_token_refresh",
  "layer": "nfr",
  "testType": "quality",
  "sourceTask": null,
  "targetFiles": ["middleware/auth.js"],
  "dependencies": ["t_auth_token"],
  "testFramework": "jest+supertest",
  "description": "Token过期→refresh→重试：accessToken过期后用refreshToken换新token，原请求重试成功",
  "testScenarios": [
    {
      "scenario": "accessToken过期 → refresh → 重试原请求成功",
      "category": "correct",
      "input": "过期accessToken请求 /api/user/profile → 401 → POST /auth/refresh → 新token",
      "output": "用新token重试 /api/user/profile → 200, 原请求数据正确"
    }
  ]
}
```

🛑 并发与幂等共 4 个 task + 限流 1 个 + Token刷新 1 个。
🛑 nfr 无 sourceTask（来自 PRD，非 task.json）。
🛑 targetFiles: 对应的 service 文件。

---

## 🛑 输出格式铁律

**JSON 文件只包含 tasks 数组。禁止附带任何元数据**（`counts`, `_meta`, `closures`, `rules_applied`, `contract_refs` 等）。这些都是 Agent 自检信息，不是测试任务数据。

# scenario 真理提取

本层产出全链路验证结果。消费并聚合 logic(flows) + navigation(jumps)。

**上层**: nfr（端点型 NFR 只依赖 scenario，页面型加 navigation，配置型加 infra/auth）。
**同层**: 各 scenario 独立（买家/商家/平台/退款互不依赖）。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "chains": [{
      "name": "买家主流程",
      "verified": true,
      "endpoints": [
        {
          "order": 1,
          "method": "GET",
          "path": "/api/products",
          "description": "商品浏览",
          "auth_required": false
        },
        {
          "order": 2,
          "method": "POST",
          "path": "/api/cart",
          "request_fields": ["skuId", "quantity", "shopId"],
          "description": "加入购物车",
          "auth_required": true,
          "role": "user"
        },
        {
          "order": 3,
          "method": "POST",
          "path": "/api/orders",
          "request_fields": ["addressId", "cartItemIds"],
          "description": "创建订单",
          "auth_required": true,
          "role": "user"
        },
        {
          "order": 4,
          "method": "POST",
          "path": "/api/orders/pay",
          "request_fields": ["orderNo"],
          "description": "支付",
          "auth_required": true,
          "role": "user"
        }
      ],
      "pages": [
        {"file": "src/pages/home/index.vue", "route": "/", "routeName": "Home"},
        {"file": "src/pages/cart/index.vue", "route": "/cart", "routeName": "Cart"}
      ]
    }]
  },
  "exposed_to_peers": {}
}
```

🛑 每个 chain 的 `endpoints[]` 按执行顺序列出。字段值从 logic 真理 `flows[].steps[]` 聚合。
🛑 `pages[]` 从 navigation 真理 `jumps[]` 的去重页面列表聚合。

### exposed_to_upper（nfr 端点型/页面型唯一数据源）

| 字段 | 类型 | 说明 |
|------|------|------|
| `chains[].name` | string | 链路名称 |
| `chains[].verified` | bool | 端到端已验证通过 |
| `chains[].endpoints[]` | object[] | 🆕 **链路包含的全部端点**（聚合 logic `steps[]`） |
| `endpoints[].order` | int | 步骤序号 |
| `endpoints[].method` | string | GET/POST/PUT/DELETE |
| `endpoints[].path` | string | 🛑 端点路径（性能/SQL注入/限流测试直接用） |
| `endpoints[].request_fields[]` | string[] | 请求 body 字段名 |
| `endpoints[].description` | string | 步骤描述 |
| `endpoints[].auth_required` | bool | 是否需要认证（决定 NFR 是否带 token） |
| `endpoints[].role` | string | 需要的角色（如 `"user"`） |
| `chains[].pages[]` | object[] | 🆕 **链路涉及的页面**（聚合 navigation `jumps[]`，去重） |
| `pages[].file` | string | 页面文件路径 |
| `pages[].route` | string | 路由路径 |
| `pages[].routeName` | string | 路由名 |

### NFR 最小依赖

| NFR 类别 | 依赖 | 说明 |
|---------|------|------|
| 端点型（性能/并发/SQL注入/限流/可用性） | **scenario** | endpoints[] 提供全部 HTTP 端点信息 |
| 页面型（XSS） | **scenario** + navigation | pages[] 提供页面路径 |
| 配置型（HTTPS/CORS） | infra | 不需要 scenario |
| Token 安全 | auth | 不需要 scenario |

### exposed_to_peers

空。各 scenario 独立验证不同用户旅程。

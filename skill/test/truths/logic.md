# logic 真理提取

本层产出跨模块验证后的流程 + 涉及的函数摘要。消费并聚合 backend_proc 真理。

**上层**: scenario（只需 logic + navigation 真理，不需要直接依赖 backend_proc）。
**同层**: 流程链——t_logic_create_order → t_logic_payment_callback。前序流程已验证。

{context}
代码:
{files}

```json
{
  "exposed_to_upper": {
    "flows": [{
      "name": "下单→支付",
      "steps": [
        {
          "order": 1,
          "method": "POST",
          "path": "/orders",
          "handler": "createOrder",
          "service": "orderService.createOrder",
          "request_fields": ["addressId", "cartItemIds"],
          "returns": "{orderNo:string, totalAmount:number, subOrders:array}",
          "throws": ["EMPTY_CART", "ADDRESS_NOT_FOUND", "STOCK_CONFLICT"]
        },
        {
          "order": 2,
          "method": "POST",
          "path": "/orders/pay",
          "handler": "pay",
          "service": "paymentService.createPayment",
          "request_fields": ["orderNo"],
          "returns": "{paymentNo:string, status:string}",
          "throws": ["ORDER_NOT_FOUND", "ALREADY_PAID", "PAYMENT_FAILED"]
        }
      ],
      "verified": true
    }]
  },
  "exposed_to_peers": {
    "upstream_flow": "下单→支付",
    "upstream_verified": true,
    "handoff_fields": ["orderNo", "totalAmount"],
    "handoff_example": {"orderNo": "ORD-20260715-001", "totalAmount": 628.00}
  }
}
```

🛑 每个 flow 的 `steps[]` 按执行顺序列出。每个 step 对应 testScenarios.process 中的一步。字段值从 backend_proc 真理和 testScenarios 中提取，不需要重新读源码。

### exposed_to_upper（scenario 唯一数据源，配合 navigation 真理）

| 字段 | 类型 | 说明 |
|------|------|------|
| `flows[].name` | string | 流程名称 |
| `flows[].verified` | bool | 跨模块组合已验证通过 |
| `flows[].steps[]` | object[] | 🆕 **流程步骤详情（聚合 backend_proc 真理）** |
| `steps[].order` | int | 步骤序号（1-based） |
| `steps[].method` | string | HTTP 方法（GET/POST/PUT/DELETE） |
| `steps[].path` | string | 端点路径 |
| `steps[].handler` | string | controller 函数名 |
| `steps[].service` | string | 🆕 对应的 service 函数（`{Service}.{fn}` 格式） |
| `steps[].request_fields` | string[] | 请求 body 字段名 |
| `steps[].returns` | string | 🆕 返回值结构（从 backend_proc 真理 `functions[].returns` 聚合） |
| `steps[].throws` | string[] | 🆕 错误码列表（从 backend_proc 真理 `functions[].throws[]` 聚合） |

### exposed_to_peers（同层流程链）

| 字段 | 类型 | 说明 |
|------|------|------|
| `upstream_flow` | string | 已验证的上游流程名称（如 `"下单→支付"`） |
| `upstream_verified` | bool | 上游流程已验证通过 |
| `handoff_fields` | string[] | 🆕 交接给下游的字段名（上游最后一步 output 中的字段，下游可直接引用） |
| `handoff_example` | object | 🆕 交接字段示例值（如 `{"orderNo": "ORD-xxx", "totalAmount": 628.00}`） |

🛑 下游任务通过 dependencies 获取此真理后，可直接在 testScenarios 中使用 `handoff_fields` 中的字段名和 `handoff_example` 中的示例值，不需要重复验证上游流程。

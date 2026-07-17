# C: scenario — 跨模块数据交接修复

继承 [logic.md](../logic.md) 通用规则。本文件只写 scenario 特有的。

## scenario 特有修复

🛑 交接点断在模块A→模块B之间。ban 指向的可能只是表象——实际是上游模块A的输出格式不对导致下游模块B接收失败。

🛑 **数据排查**: 全链路 401/404 大面积失败 → 先检查 logic 真理 `flows[].steps[]` 中端点路径/method 是否正确 → 再查 scenario 真理 `chains[].endpoints[]` 的 auth_required 配置。

### 定位策略

```
B 的 ban: f=scenario|source|paymentService.js|DATA_INCONSISTENT

不一定只修 paymentService.js。交接链数据流:
  POST /cart → POST /order → POST /payment
                        ↑ 断点

排查链路:
  1. POST /order 返回的 orderId 格式? 是 number 还是 {orderId}?
  2. POST /cart 加购的量是否正确?
  3. 上游模块输出字段名不对导致下游接收失败 → 修上游而非下游
```

### 常见修复模式

```javascript
// 场景: 加购→下单 交接点断

// 问题: 第4步 POST /cart 返回 cartItem={id, productId, quantity}
//       第5步 POST /order 期望 items=[{productId, quantity}]
//       但中间没有把 cartItem 转成 items 格式
// → 修复: 前端/controller 做格式转换
//   const items = cartItems.map(c => ({ productId: c.productId, quantity: c.quantity }))

// 问题: 第1步 GET /categories 返回的分类 id 是 string
//       第2步 GET /products?categoryId=1 → 数据库 category_id 是 INT
//       类型不匹配导致查不出数据
// → 修复: controller 统一 parseInt(categoryId, 10)

// 问题: 第4步用了 buyer token，第5步 token 过期(expiresIn 太短)
// → 修复: 延长 token 过期时间，或测试在每步前重新获取 token
```

### 状态不一致修复

```javascript
// 交接链走完发现 order.status 应该是 'paid' 实际是 'pending_pay'

// 排查: POST /payment 返回了201，但实际没有 UPDATE orders
// load_d_card 读 payment controller:
//   发现: payment 成功后只 INSERT payments 记录
//        但没有 UPDATE orders SET status='paid'
// → 修复: paymentService 里加 UPDATE orders SET status='paid' WHERE id=?
```

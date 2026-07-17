# C: logic — 跨功能数据流修复

继承 [logic.md](../logic.md) 通用规则。本文件只写 logic 特有的。

## logic 特有修复

🛑 故障通常在上游输出和下游输入之间。修的不是单点，是**数据对接处**。

### 跨功能数据一致性问题

```javascript
// 修复前: 支付服务检查 order 状态，但 status 值与下单时写入的不一致

// services/orderService.js — 下单时写入
await conn.execute('INSERT INTO orders (userId, total, status) VALUES (?, ?, ?)',
  [userId, total, 'pending_payment']);  // ← 写的是 'pending_payment'

// services/paymentService.js — 支付时检查
const [order] = await db.query('SELECT status FROM orders WHERE id=?', [orderId]);
if (order.status !== 'pending_pay') {   // ← 检查的是 'pending_pay'
  throw new Error('ORDER_NOT_PENDING'); // ← 永远匹配不上!
}
// → 修复: 统一为 'pending_pay'，对齐契约
```

### 跨步骤数据类型不一致

```javascript
// 修复前: 步骤1返回 orderId=number, 步骤2接收时当 string
// controller: POST /order → res.json({ orderId: 100 })  // number
// controller: POST /payment → const orderId = req.body.orderId  // req.body 是 string "100"
// service: WHERE id=? → [orderId]  → 可能类型不匹配导致 SQL 索引失效全表扫

// 修复: controller 统一 parseInt
const orderId = parseInt(req.body.orderId, 10);
```

### 补偿事务缺失

```javascript
// 修复前: 退款只 INSERT refund 记录，不恢复库存
async function createRefund(orderId, reason) {
  await db.query('INSERT INTO refunds (orderId, reason) VALUES (?, ?)', [orderId, reason]);
  // 缺: 恢复库存
  // 缺: 更新 order 状态
  // 缺: 事务包裹
}

// 修复后:
async function createRefund(orderId, reason) {
  const conn = await db.beginTransaction();
  try {
    const [order] = await conn.execute('SELECT status FROM orders WHERE id=? FOR UPDATE', [orderId]);
    if (order[0].status !== 'paid') throw new Error('CANNOT_REFUND');
    // 恢复库存 ← MISSING_COMPENSATION
    await conn.execute(
      'UPDATE products p JOIN order_items oi ON p.id=oi.product_id SET p.stock=p.stock+oi.quantity WHERE oi.order_id=?',
      [orderId]
    );
    await conn.execute('INSERT INTO refunds ...');
    await conn.execute("UPDATE orders SET status='refunding' WHERE id=?", [orderId]); // ← STALE_STATE
    await conn.commit();
  } catch (err) {
    await conn.rollback();
    throw err;
  }
}
```

### 幂等缺失

```javascript
// 修复: 下单前检查幂等键
async function createOrder(userId, items, idempotentKey) {
  if (idempotentKey) {
    const [existing] = await db.query(
      'SELECT id FROM orders WHERE idempotent_key=?', [idempotentKey]
    );
    if (existing.length > 0) {
      return { orderId: existing[0].id, duplicated: true }; // ← MISSING_IDEMPOTENT
    }
  }
  // ... 正常下单，写入 idempotent_key
}
```

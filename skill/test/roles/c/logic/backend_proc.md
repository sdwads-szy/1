# C: backend_proc — 单功能处理链修复

继承 [logic.md](../logic.md) 通用规则。本文件只写 backend_proc 特有的。

## backend_proc 特有修复

🛑 按 ban 的 f 字段定位文件，按 process 步骤序号定位代码行。

### 事务修复（高频）

```javascript
// 修复前: 缺事务
async function createOrder(userId, items) {
  const stock = await db.query('SELECT stock FROM products WHERE id=?', [items[0].productId]);
  if (stock[0][0].stock < items[0].quantity) throw new Error('库存不足');
  await db.query('UPDATE products SET stock=stock-? WHERE id=?', [items[0].quantity, items[0].productId]);
  await db.query('INSERT INTO orders ...');
  return { orderId: 100, status: 'pending_pay' };
}

// 修复后: 加事务
async function createOrder(userId, items) {
  const conn = await db.beginTransaction();          // ← MISSING_TX
  try {
    const [rows] = await conn.execute(               // ← TX_CONN_MISUSE: db→conn
      'SELECT stock FROM products WHERE id=? FOR UPDATE', // ← MISSING_LOCK: +FOR UPDATE
      [items[0].productId]
    );
    if (rows[0].stock < items[0].quantity) {
      await conn.rollback();                          // ← MISSING_ROLLBACK
      throw new Error('INSUFFICIENT_STOCK');         // ← 必须是具体错误码
    }
    await conn.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',  // ← WRONG_STOCK
      [items[0].quantity, items[0].productId, items[0].quantity]);
    const [orderResult] = await conn.execute('INSERT INTO orders ...');
    await conn.execute('INSERT INTO order_items ...'); // ← PARTIAL_WRITE
    await conn.commit();                               // ← MISSING_COMMIT
    return { orderId: orderResult.insertId, status: 'pending_pay' }; // ← WRONG_OUTPUT
  } catch (err) {
    await conn.rollback();
    throw err;                                         // ← 不能吞异常
  }
}
```

### 错误码修复对照

| ban 子类型 | 修复 |
|-----------|------|
| MISSING_TX | `const conn = await db.beginTransaction()` |
| MISSING_COMMIT | `await conn.commit()` 在 try 末尾 |
| MISSING_ROLLBACK | `await conn.rollback()` 在 catch 块 |
| MISSING_LOCK | SQL 加 `FOR UPDATE` |
| TX_CONN_MISUSE | `db.query()` → `conn.execute()` |
| WRONG_STOCK | `UPDATE SET stock=stock-?` 用实际 quantity |
| WRONG_ORDER | 调整代码行顺序对齐 process 步骤 |
| WRONG_OUTPUT | return 补全字段: `{orderId:result.insertId, orderNo, totalPrice, status}` |
| PARAM_MISMATCH | 函数签名对齐: `createOrder(userId, items)` |
| PARTIAL_WRITE | 补 `INSERT INTO order_items` |

const db = require('../config/db');

/**
 * 乐观锁扣减库存（独立事务）
 * 场景树 §3.5: 库存预占 — 乐观锁 CAS
 */
async function deductInventory(skuId, shopId, quantity) {
  const conn = await db.getConnection();
  try {
    const [rows] = await conn.execute(
      'SELECT stock, version FROM inventories WHERE sku_id=? AND shop_id=?',
      [skuId, shopId]
    );
    if (!rows.length) throw new Error('INVENTORY_NOT_FOUND');
    const { stock, version } = rows[0];
    if (stock < quantity) throw new Error('INSUFFICIENT_STOCK');
    const [res] = await conn.execute(
      'UPDATE inventories SET stock=stock-?, frozen_stock=frozen_stock+?, version=version+1 WHERE sku_id=? AND shop_id=? AND version=? AND stock>=?',
      [quantity, quantity, skuId, shopId, version, quantity]
    );
    if (res.affectedRows === 0) throw new Error('INSUFFICIENT_STOCK');
    await conn.commit();
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

/**
 * 恢复库存（释放预占）
 * 场景树: 订单取消/退款 — 释放 frozen_stock
 */
async function restoreInventory(skuId, shopId, quantity) {
  const conn = await db.getConnection();
  try {
    const [res] = await conn.execute(
      'UPDATE inventories SET stock=stock+?, frozen_stock=frozen_stock-? WHERE sku_id=? AND shop_id=?',
      [quantity, quantity, skuId, shopId]
    );
    await conn.commit();
    return res.affectedRows > 0;
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

module.exports = { deductInventory, restoreInventory };

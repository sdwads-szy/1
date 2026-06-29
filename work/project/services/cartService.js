const db = require('../config/db');

const MAX_QUANTITY = 99;

/**
 * 获取用户购物车列表，关联 SKU 和商品信息
 * @param {number} userId - 用户 ID
 * @returns {Promise<{items: Array<{cartId, skuId, productTitle, productId, specCombo, price, quantity, stock, image}>, total: number}>}
 */
async function getCartItems(userId) {
  const sql = `
    SELECT c.id AS cartId, c.sku_id AS skuId, c.quantity,
           s.spec_combo AS specCombo, s.price, s.stock, s.image,
           p.title AS productTitle, p.id AS productId
    FROM carts c
    JOIN skus s ON c.sku_id = s.id
    JOIN products p ON s.product_id = p.id
    WHERE c.user_id = ?
    ORDER BY c.created_at DESC
  `;
  const rows = await db.query(sql, [userId]);

  const items = rows.map(row => ({
    cartId: row.cartId,
    skuId: row.skuId,
    productTitle: row.productTitle,
    productId: row.productId,
    specCombo: row.specCombo,
    price: row.price.toString(),
    quantity: row.quantity,
    stock: row.stock,
    image: row.image || ''
  }));

  return { items, total: items.length };
}

/**
 * 加入购物车：校验库存 → UPSERT（同用户同 SKU 则数量累加）
 * @param {number} userId - 用户 ID
 * @param {number} skuId - SKU ID
 * @param {number} quantity - 本次加购数量
 * @returns {Promise<{success: boolean, cartCount: number}>}
 */
async function addToCart(userId, skuId, quantity) {
  const qty = parseInt(quantity) || 0;
  if (qty < 1 || qty > MAX_QUANTITY) {
    throw new Error('QUANTITY_EXCEED');
  }

  // 查询 SKU 是否存在及库存
  const skuRows = await db.query('SELECT id, stock FROM skus WHERE id = ?', [skuId]);
  if (!skuRows.length) {
    throw new Error('PRODUCT_NOT_FOUND');
  }
  const sku = skuRows[0];

  // 查询该用户是否已有此 SKU 的购物车记录
  const cartRows = await db.query(
    'SELECT id, quantity FROM carts WHERE user_id = ? AND sku_id = ?',
    [userId, skuId]
  );

  const existingQty = cartRows.length > 0 ? cartRows[0].quantity : 0;
  const newTotal = existingQty + qty;

  // 库存校验（不能超过 SKU 当前库存）
  if (newTotal > sku.stock) {
    throw new Error('SKU_OUT_OF_STOCK');
  }

  // 数量上限校验
  if (newTotal > MAX_QUANTITY) {
    throw new Error('QUANTITY_EXCEED');
  }

  // UPSERT：存在则累加数量，不存在则插入
  await db.query(
    `INSERT INTO carts (user_id, sku_id, quantity) VALUES (?, ?, ?)
     ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)`,
    [userId, skuId, qty]
  );

  // 返回当前购物车商品种类数
  const countRows = await db.query(
    'SELECT COUNT(*) AS cnt FROM carts WHERE user_id = ?',
    [userId]
  );

  return { success: true, cartCount: countRows[0].cnt };
}

/**
 * 更新购物车商品数量
 * @param {number} cartId - 购物车记录 ID
 * @param {number} userId - 用户 ID（权限校验）
 * @param {number} quantity - 新数量
 */
async function updateQuantity(cartId, userId, quantity) {
  const qty = parseInt(quantity) || 0;
  if (qty < 1 || qty > MAX_QUANTITY) {
    throw new Error('QUANTITY_EXCEED');
  }

  // 查询购物车记录并校验归属
  const cartRows = await db.query('SELECT id, user_id, sku_id FROM carts WHERE id = ?', [cartId]);
  if (!cartRows.length) {
    throw new Error('NOT_FOUND');
  }
  if (cartRows[0].user_id !== userId) {
    throw new Error('FORBIDDEN');
  }

  // 校验 SKU 库存
  const skuRows = await db.query('SELECT stock FROM skus WHERE id = ?', [cartRows[0].sku_id]);
  if (!skuRows.length) {
    throw new Error('PRODUCT_NOT_FOUND');
  }

  if (qty > skuRows[0].stock) {
    throw new Error('SKU_OUT_OF_STOCK');
  }

  await db.query('UPDATE carts SET quantity = ? WHERE id = ?', [qty, cartId]);
}

/**
 * 删除购物车商品
 * @param {number} cartId - 购物车记录 ID
 * @param {number} userId - 用户 ID（权限校验）
 */
async function removeItem(cartId, userId) {
  const cartRows = await db.query('SELECT id, user_id FROM carts WHERE id = ?', [cartId]);
  if (!cartRows.length) {
    throw new Error('NOT_FOUND');
  }
  if (cartRows[0].user_id !== userId) {
    throw new Error('FORBIDDEN');
  }

  await db.query('DELETE FROM carts WHERE id = ?', [cartId]);
}

module.exports = { getCartItems, addToCart, updateQuantity, removeItem };

const db = require('../config/db');

/**
 * 获取用户购物车，按店铺分组，并标注商品状态
 * @param {number} userId
 * @returns {{ shops: Array<{shopId, shopName, shopStatus, items: Array}> }}
 */
async function getCart(userId) {
  const rows = await db.query(
    `SELECT
       ci.id,
       ci.sku_id,
       ci.shop_id,
       ci.quantity,
       ci.checked,
       s.spec_name,
       s.price,
       s.image AS sku_image,
       sp.id AS spu_id,
       sp.name AS spu_name,
       sp.default_image,
       sp.status AS spu_status,
       sh.name AS shop_name,
       sh.status AS shop_status,
       COALESCE(inv.stock, 0) AS stock,
       COALESCE(inv.frozen_stock, 0) AS frozen_stock
     FROM cart_items ci
     JOIN sku s ON ci.sku_id = s.id
     JOIN spu sp ON s.spu_id = sp.id
     JOIN shops sh ON ci.shop_id = sh.id
     LEFT JOIN inventories inv ON ci.sku_id = inv.sku_id AND ci.shop_id = inv.shop_id
     WHERE ci.user_id = ?
     ORDER BY ci.created_at DESC`,
    [userId]
  );

  // 按店铺分组
  const shopMap = new Map();
  for (const row of rows) {
    const shopKey = row.shop_id;
    if (!shopMap.has(shopKey)) {
      shopMap.set(shopKey, {
        shopId: row.shop_id,
        shopName: row.shop_name,
        shopStatus: row.shop_status,
        items: [],
      });
    }
    const shop = shopMap.get(shopKey);

    // 判断商品可用状态
    let itemStatus = 'available';
    if (row.shop_status === 'frozen') {
      itemStatus = 'shop_frozen';
    } else if (row.spu_status !== 'listed') {
      itemStatus = 'delisted';
    } else if (row.stock < row.quantity) {
      // 可用库存 = stock - frozen_stock，frozen_stock 是下单预占
      const available = Math.max(0, row.stock - row.frozen_stock);
      if (available <= 0) {
        itemStatus = 'out_of_stock';
      } else if (available < row.quantity) {
        itemStatus = 'insufficient_stock';
      }
    }

    shop.items.push({
      id: row.id,
      skuId: row.sku_id,
      spuId: row.spu_id,
      spuName: row.spu_name,
      specName: row.spec_name,
      price: row.price,
      image: row.sku_image || row.default_image,
      quantity: row.quantity,
      checked: !!row.checked,
      stock: row.stock,
      availableStock: Math.max(0, row.stock - row.frozen_stock),
      spuStatus: row.spu_status,
      itemStatus,
    });
  }

  return {
    shops: Array.from(shopMap.values()),
  };
}

/**
 * 添加商品到购物车（UPSERT：同一用户+SKU+店铺，存在则累加数量）
 * @param {number} userId
 * @param {number} skuId
 * @param {number} quantity
 * @param {number} shopId
 * @returns {{ cartItem: object }}
 */
async function addToCart(userId, skuId, quantity, shopId) {
  const conn = await db.beginTransaction();
  try {
    // 1. 校验 SKU 存在
    const [skuRows] = await conn.execute(
      'SELECT id, spu_id, spec_name, price, image FROM sku WHERE id = ?',
      [skuId]
    );
    if (!skuRows.length) {
      await conn.rollback();
      throw new Error('SKU_NOT_FOUND');
    }
    const sku = skuRows[0];

    // 2. 校验 SPU 存在且已上架
    const [spuRows] = await conn.execute(
      'SELECT id, name, status, default_image, shop_id FROM spu WHERE id = ?',
      [sku.spu_id]
    );
    if (!spuRows.length) {
      await conn.rollback();
      throw new Error('SPU_NOT_FOUND');
    }
    const spu = spuRows[0];
    if (spu.status !== 'listed') {
      await conn.rollback();
      throw new Error('SPU_NOT_LISTED');
    }

    // 3. 校验店铺营业中
    const [shopRows] = await conn.execute(
      'SELECT id, status FROM shops WHERE id = ?',
      [spu.shop_id]
    );
    if (!shopRows.length) {
      await conn.rollback();
      throw new Error('SHOP_NOT_FOUND');
    }
    if (shopRows[0].status !== 'open') {
      await conn.rollback();
      throw new Error('SHOP_NOT_OPEN');
    }

    // 3b. 校验 SKU 归属于该店铺（spu.shop_id === shopId）
    if (spu.shop_id !== shopId) {
      await conn.rollback();
      throw new Error('SKU_NOT_BELONG_TO_SHOP');
    }

    // 4. 校验库存
    const [invRows] = await conn.execute(
      'SELECT stock, frozen_stock FROM inventories WHERE sku_id = ? AND shop_id = ?',
      [skuId, shopId]
    );
    const availableStock = invRows.length
      ? Math.max(0, invRows[0].stock - invRows[0].frozen_stock)
      : 0;

    // 5. 检查是否已有同 SKU+店铺 的购物车项
    const [existing] = await conn.execute(
      'SELECT id, quantity FROM cart_items WHERE user_id = ? AND sku_id = ? AND shop_id = ?',
      [userId, skuId, shopId]
    );

    if (existing.length) {
      // UPSERT: 累加数量
      const newQty = existing[0].quantity + quantity;
      if (newQty > availableStock) {
        await conn.rollback();
        throw new Error('STOCK_INSUFFICIENT');
      }
      await conn.execute(
        'UPDATE cart_items SET quantity = ?, checked = 1 WHERE id = ? AND user_id = ?',
        [newQty, existing[0].id, userId]
      );
      await conn.commit();
      return {
        cartItem: {
          id: existing[0].id,
          skuId,
          shopId,
          quantity: newQty,
          checked: true,
        },
      };
    }

    // 新插入
    if (quantity > availableStock) {
      await conn.rollback();
      throw new Error('STOCK_INSUFFICIENT');
    }

    const [result] = await conn.execute(
      'INSERT INTO cart_items (user_id, sku_id, shop_id, quantity, checked) VALUES (?, ?, ?, ?, 1)',
      [userId, skuId, shopId, quantity]
    );

    await conn.commit();
    return {
      cartItem: {
        id: result.insertId,
        skuId,
        shopId,
        quantity,
        checked: true,
      },
    };
  } catch (err) {
    await conn.rollback();
    throw err;
  }
}

/**
 * 修改购物车商品数量
 * @param {number} userId
 * @param {number} cartItemId
 * @param {number} quantity
 * @returns {{ cartItem: object }}
 */
async function updateCartItem(userId, cartItemId, quantity) {
  // 验证购物车项存在且属于当前用户
  const rows = await db.query(
    `SELECT ci.id, ci.sku_id, ci.shop_id,
            COALESCE(inv.stock, 0) AS stock,
            COALESCE(inv.frozen_stock, 0) AS frozen_stock
     FROM cart_items ci
     LEFT JOIN inventories inv ON ci.sku_id = inv.sku_id AND ci.shop_id = inv.shop_id
     WHERE ci.id = ? AND ci.user_id = ?`,
    [cartItemId, userId]
  );
  if (!rows.length) {
    throw new Error('CART_ITEM_NOT_FOUND');
  }

  const item = rows[0];
  const available = Math.max(0, item.stock - item.frozen_stock);
  if (quantity > available) {
    throw new Error('INSUFFICIENT_STOCK');
  }

  await db.query(
    'UPDATE cart_items SET quantity = ? WHERE id = ? AND user_id = ?',
    [quantity, cartItemId, userId]
  );

  return {
    cartItem: {
      id: cartItemId,
      skuId: item.sku_id,
      shopId: item.shop_id,
      quantity,
    },
  };
}

/**
 * 删除购物车单品
 * @param {number} userId
 * @param {number} cartItemId
 */
async function removeCartItem(userId, cartItemId) {
  const result = await db.query(
    'DELETE FROM cart_items WHERE id = ? AND user_id = ?',
    [cartItemId, userId]
  );
  if (!result.affectedRows) {
    throw new Error('CART_ITEM_NOT_FOUND');
  }
}

/**
 * 批量勾选/取消勾选
 * @param {number} userId
 * @param {number[]} cartItemIds
 * @param {boolean} checked
 * @returns {{ affectedCount: number }}
 */
async function batchCheck(userId, cartItemIds, checked) {
  if (cartItemIds.length === 0) return { affectedCount: 0 };

  const placeholders = cartItemIds.map(() => '?').join(',');
  const params = [checked ? 1 : 0, userId, ...cartItemIds];

  const result = await db.query(
    `UPDATE cart_items SET checked = ? WHERE user_id = ? AND id IN (${placeholders})`,
    params
  );

  return { affectedCount: result.affectedRows };
}

/**
 * 清空用户购物车
 * @param {number} userId
 */
async function clearCart(userId) {
  await db.query('DELETE FROM cart_items WHERE user_id = ?', [userId]);
}

module.exports = {
  getCart,
  addToCart,
  updateCartItem,
  removeCartItem,
  batchCheck,
  clearCart,
};

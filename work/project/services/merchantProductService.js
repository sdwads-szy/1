const db = require('../config/db');

// ═══════════════════════════════════════════════════════════════
// 内部辅助：根据 merchants.id 查询店铺 id + 营业状态
// ═══════════════════════════════════════════════════════════════
async function getShopByMerchant(merchantId) {
  const rows = await db.query(
    'SELECT s.id AS shop_id, s.status AS shop_status FROM shops s WHERE s.merchant_id = ?',
    [merchantId]
  );
  if (!rows.length) throw new Error('SHOP_NOT_FOUND');
  return rows[0];
}

// ═══════════════════════════════════════════════════════════════
// listProducts — 本店商品列表（分页 + 状态筛选）
// ═══════════════════════════════════════════════════════════════
async function listProducts(merchantId, status, page, pageSize) {
  const shop = await getShopByMerchant(merchantId);
  const offset = (page - 1) * pageSize;

  const whereClause = status
    ? 'WHERE spu.shop_id = ? AND spu.status = ?'
    : 'WHERE spu.shop_id = ?';

  const baseParams = status ? [shop.shop_id, status] : [shop.shop_id];

  // 总数
  const countRows = await db.query(
    'SELECT COUNT(*) AS total FROM spu ' + whereClause,
    baseParams
  );
  const total = countRows[0].total;

  // 列表：JOIN sku 取最低价
  const dataSql =
    'SELECT spu.id, spu.category_id, spu.name, spu.default_image, spu.status, spu.sales, ' +
    'MIN(sku.price) AS min_price ' +
    'FROM spu LEFT JOIN sku ON sku.spu_id = spu.id ' +
    whereClause + ' ' +
    'GROUP BY spu.id ORDER BY spu.updated_at DESC LIMIT ? OFFSET ?';

  const listParams = [...baseParams, pageSize, offset];
  const rows = await db.query(dataSql, listParams);

  return { list: rows, total, page, pageSize };
}

// ═══════════════════════════════════════════════════════════════
// publishProduct — 商家发布商品
//   Step 1: 校验店铺营业中
//   Step 2: 校验每个 SKU 价格 > 0
//   Step 3-7: 单事务写入 spu → sku → inventories → product_images
// ═══════════════════════════════════════════════════════════════
async function publishProduct(merchantId, categoryId, name, description, skus, images) {
  // Step 1: 店铺必须营业中
  const shop = await getShopByMerchant(merchantId);
  if (shop.shop_status !== 'open') {
    throw new Error('SHOP_FROZEN');
  }

  // Step 2: SKU 价格校验
  for (const sku of skus) {
    if (!sku.price || parseFloat(sku.price) <= 0) {
      throw new Error('SKU_PRICE_INVALID');
    }
  }

  const defaultImage = (images && images.length > 0) ? images[0] : null;

  // Step 3-7: 事务
  const conn = await db.beginTransaction();
  try {
    // Step 3: INSERT spu
    const spuResult = await conn.execute(
      'INSERT INTO spu (shop_id, category_id, name, description, default_image, status) VALUES (?, ?, ?, ?, ?, ?)',
      [shop.shop_id, categoryId, name, description || null, defaultImage, 'draft']
    );
    const spuId = spuResult.insertId;

    // Step 4: 批量 INSERT sku
    const skuRecords = [];
    for (const sku of skus) {
      const skuResult = await conn.execute(
        'INSERT INTO sku (spu_id, spec_name, price, image) VALUES (?, ?, ?, ?)',
        [spuId, sku.specName, sku.price, sku.image || null]
      );
      skuRecords.push({ id: skuResult.insertId, stock: sku.stock || 0 });
    }

    // Step 5: 批量 INSERT inventories（每个 SKU 一条，初始 frozen_stock=0 version=0）
    for (const rec of skuRecords) {
      await conn.execute(
        'INSERT INTO inventories (sku_id, shop_id, stock, frozen_stock, version) VALUES (?, ?, ?, 0, 0)',
        [rec.id, shop.shop_id, rec.stock]
      );
    }

    // Step 6: 批量 INSERT product_images
    if (images && images.length > 0) {
      for (let i = 0; i < images.length; i++) {
        await conn.execute(
          'INSERT INTO product_images (spu_id, url, sort) VALUES (?, ?, ?)',
          [spuId, images[i], i + 1]
        );
      }
    }

    // Step 7: COMMIT
    await db.commit(conn);

    return { productId: spuId, status: 'draft' };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

// ═══════════════════════════════════════════════════════════════
// updateProduct — 编辑商品
//   校验所有权 → 单事务更新 SPU + 可选全量替换 SKU/图片
// ═══════════════════════════════════════════════════════════════
async function updateProduct(merchantId, productId, updates) {
  const shop = await getShopByMerchant(merchantId);

  // 所有权校验
  const spuRows = await db.query(
    'SELECT id, shop_id FROM spu WHERE id = ?',
    [productId]
  );
  if (!spuRows.length) throw new Error('PRODUCT_NOT_FOUND');
  if (spuRows[0].shop_id !== shop.shop_id) throw new Error('NOT_OWN_PRODUCT');

  const conn = await db.beginTransaction();
  try {
    // ——— SPU 字段更新 ———
    const setClauses = [];
    const setParams = [];

    if (updates.categoryId !== undefined) {
      setClauses.push('category_id = ?');
      setParams.push(updates.categoryId);
    }
    if (updates.name !== undefined) {
      setClauses.push('name = ?');
      setParams.push(updates.name);
    }
    if (updates.description !== undefined) {
      setClauses.push('description = ?');
      setParams.push(updates.description);
    }
    if (updates.images !== undefined) {
      setClauses.push('default_image = ?');
      setParams.push(updates.images.length > 0 ? updates.images[0] : null);
    }

    if (setClauses.length > 0) {
      setParams.push(productId);
      await conn.execute(
        `UPDATE spu SET ${setClauses.join(', ')} WHERE id = ?`,
        setParams
      );
    }

    // ——— SKU 全量替换 ———
    if (updates.skus !== undefined) {
      // 校验价格
      for (const sku of updates.skus) {
        if (!sku.price || parseFloat(sku.price) <= 0) {
          throw new Error('SKU_PRICE_INVALID');
        }
      }

      // 删除旧库存（通过子查询定位本 SPU 的 SKU）
      await conn.execute(
        'DELETE FROM inventories WHERE sku_id IN (SELECT id FROM sku WHERE spu_id = ?)',
        [productId]
      );
      // 删除旧 SKU
      await conn.execute('DELETE FROM sku WHERE spu_id = ?', [productId]);

      // 写入新 SKU + 库存
      for (const sku of updates.skus) {
        const r = await conn.execute(
          'INSERT INTO sku (spu_id, spec_name, price, image) VALUES (?, ?, ?, ?)',
          [productId, sku.specName, sku.price, sku.image || null]
        );
        await conn.execute(
          'INSERT INTO inventories (sku_id, shop_id, stock, frozen_stock, version) VALUES (?, ?, ?, 0, 0)',
          [r.insertId, shop.shop_id, sku.stock || 0]
        );
      }
    }

    // ——— 图片全量替换 ———
    if (updates.images !== undefined) {
      await conn.execute('DELETE FROM product_images WHERE spu_id = ?', [productId]);
      for (let i = 0; i < updates.images.length; i++) {
        await conn.execute(
          'INSERT INTO product_images (spu_id, url, sort) VALUES (?, ?, ?)',
          [productId, updates.images[i], i + 1]
        );
      }
    }

    await db.commit(conn);
    return { productId };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = { listProducts, publishProduct, updateProduct };

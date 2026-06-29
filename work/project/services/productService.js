const db = require('../config/db');
const redis = require('../config/redis');

const CACHE_PRODUCT_DETAIL = 'product:detail:';
const CACHE_PRODUCT_LIST = 'product:list:';
const CACHE_TTL = 300;

/**
 * 安全缓存读取
 */
async function cacheGet(key) {
  try {
    const val = await redis.get(key);
    return val ? JSON.parse(val) : null;
  } catch (_) {
    return null;
  }
}

/**
 * 安全缓存写入
 */
async function cacheSet(key, data, ttl) {
  try {
    await redis.set(key, JSON.stringify(data));
    await redis.expire(key, ttl);
  } catch (_) { /* 缓存失败不影响业务 */ }
}

/**
 * 安全缓存删除
 */
async function cacheDel(key) {
  try {
    await redis.del(key);
  } catch (_) { /* 忽略 */ }
}

/**
 * 前台商品列表
 * 支持分类筛选、排序、分页、价格区间。结果缓存 Redis。
 */
async function listProducts({ categoryId, sort, page, pageSize, priceMin, priceMax }) {
  const p = parseInt(page) || 1;
  const ps = Math.min(parseInt(pageSize) || 20, 100);
  const offset = (p - 1) * ps;

  const cacheKey = `${CACHE_PRODUCT_LIST}${categoryId || 'all'}_${sort || 'newest'}_${p}_${ps}_${priceMin || ''}_${priceMax || ''}`;
  const cached = await cacheGet(cacheKey);
  if (cached) return cached;

  const conditions = ["p.status = 'listed'"];
  const params = [];

  if (categoryId) {
    conditions.push('p.category_id = ?');
    params.push(parseInt(categoryId));
  }

  if (priceMin !== undefined && priceMin !== null && priceMin !== '') {
    conditions.push('EXISTS (SELECT 1 FROM skus s WHERE s.product_id = p.id AND s.price >= ?)');
    params.push(parseFloat(priceMin));
  }

  if (priceMax !== undefined && priceMax !== null && priceMax !== '') {
    conditions.push('EXISTS (SELECT 1 FROM skus s WHERE s.product_id = p.id AND s.price <= ?)');
    params.push(parseFloat(priceMax));
  }

  const whereClause = 'WHERE ' + conditions.join(' AND ');

  const ALLOWED_SORT = {
    price_asc: 'min_price ASC',
    price_desc: 'min_price DESC',
    newest: 'p.created_at DESC',
    sales: 'sales DESC'
  };
  const orderClause = 'ORDER BY ' + (ALLOWED_SORT[sort] || ALLOWED_SORT.newest);

  const countResult = await db.query(
    `SELECT COUNT(*) as total FROM products p ${whereClause}`,
    params
  );
  const total = countResult[0].total;

  const list = await db.query(
    `SELECT p.id, p.title, p.main_image, p.shop_id,
            (SELECT MIN(sku.price) FROM skus sku WHERE sku.product_id = p.id) as min_price,
            COALESCE((SELECT SUM(oi.quantity)
              FROM order_items oi
              JOIN orders o ON oi.order_id = o.id
              WHERE oi.sku_id IN (SELECT id FROM skus WHERE product_id = p.id)
                AND o.status IN ('paid','shipped','received','completed')), 0) as sales
     FROM products p
     ${whereClause}
     ${orderClause}
     LIMIT ? OFFSET ?`,
    [...params, ps, offset]
  );

  const formattedList = list.map(item => ({
    ...item,
    min_price: item.min_price !== null ? String(item.min_price) : '0.00',
    sales: Number(item.sales)
  }));

  const result = { list: formattedList, total, page: p, pageSize: ps };
  await cacheSet(cacheKey, result, CACHE_TTL);
  return result;
}

/**
 * 前台商品详情
 * 含 SKU 列表与店铺名，结果缓存 Redis。
 */
async function getProductDetail(id) {
  const productId = parseInt(id) || 0;
  const cacheKey = CACHE_PRODUCT_DETAIL + productId;
  const cached = await cacheGet(cacheKey);
  if (cached) return cached;

  const rows = await db.query(
    `SELECT p.id, p.shop_id, p.category_id, p.title, p.description, p.status, p.main_image, p.created_at,
            sh.name AS shop_name
     FROM products p
     JOIN shops sh ON p.shop_id = sh.id
     WHERE p.id = ? AND p.status IN ('listed','delisted')`,
    [productId]
  );

  if (!rows.length) throw new Error('PRODUCT_NOT_FOUND');
  const product = rows[0];

  const skuRows = await db.query(
    'SELECT id, spec_combo, price, stock, image FROM skus WHERE product_id = ?',
    [productId]
  );

  const result = {
    id: product.id,
    title: product.title,
    description: product.description,
    mainImage: product.main_image,
    shopId: product.shop_id,
    shopName: product.shop_name,
    categoryId: product.category_id,
    status: product.status,
    createdAt: product.created_at,
    skus: skuRows.map(s => ({
      id: s.id,
      specCombo: s.spec_combo,
      price: String(s.price),
      stock: s.stock,
      image: s.image
    }))
  };

  await cacheSet(cacheKey, result, CACHE_TTL);
  return result;
}

/**
 * 商家 — 获取自己的商品列表
 */
async function getMerchantProducts(shopId, { status, page, pageSize }) {
  const p = parseInt(page) || 1;
  const ps = Math.min(parseInt(pageSize) || 20, 100);
  const offset = (p - 1) * ps;
  const conditions = ['p.shop_id = ?'];
  const params = [shopId];

  if (status) {
    conditions.push('p.status = ?');
    params.push(status);
  }

  const whereClause = 'WHERE ' + conditions.join(' AND ');

  const countResult = await db.query(
    `SELECT COUNT(*) as total FROM products p ${whereClause}`,
    params
  );
  const total = countResult[0].total;

  const list = await db.query(
    `SELECT p.id, p.title, p.main_image, p.status, p.category_id, p.created_at,
            (SELECT MIN(sku.price) FROM skus sku WHERE sku.product_id = p.id) as min_price,
            (SELECT SUM(sku.stock) FROM skus sku WHERE sku.product_id = p.id) as total_stock
     FROM products p
     ${whereClause}
     ORDER BY p.created_at DESC
     LIMIT ? OFFSET ?`,
    [...params, ps, offset]
  );

  return {
    list: list.map(item => ({
      ...item,
      min_price: item.min_price !== null ? String(item.min_price) : '0.00',
      total_stock: item.total_stock || 0
    })),
    total,
    page: p,
    pageSize: ps
  };
}

/**
 * 商家 — 获取单个商品详情
 */
async function getMerchantProductDetail(productId, shopId) {
  const id = parseInt(productId) || 0;
  const rows = await db.query(
    'SELECT id, shop_id, category_id, title, description, status, main_image, created_at, updated_at FROM products WHERE id = ?',
    [id]
  );
  if (!rows.length) throw new Error('PRODUCT_NOT_FOUND');
  if (rows[0].shop_id !== shopId) throw new Error('NOT_PRODUCT_OWNER');

  const skuRows = await db.query(
    'SELECT id, spec_combo, price, stock, image FROM skus WHERE product_id = ?',
    [id]
  );

  return {
    ...rows[0],
    skus: skuRows.map(s => ({
      id: s.id,
      specCombo: s.spec_combo,
      price: String(s.price),
      stock: s.stock,
      image: s.image
    }))
  };
}

/**
 * 商家 — 发布商品
 * 事务：商品 + SKU + 快照，状态 pending_review
 */
async function createProduct(shopId, { categoryId, title, description, mainImage, skus }) {
  // 校验店铺状态
  const shopRows = await db.query(
    "SELECT id FROM shops WHERE id = ? AND status = 'active'",
    [shopId]
  );
  if (!shopRows.length) throw new Error('SHOP_NOT_ACTIVE');

  // 校验类目
  const catId = parseInt(categoryId) || 0;
  const catRows = await db.query(
    "SELECT id FROM categories WHERE id = ? AND status = 'active'",
    [catId]
  );
  if (!catRows.length) throw new Error('CATEGORY_INVALID');

  // 校验 SKU
  if (!skus || !Array.isArray(skus) || !skus.length) {
    throw new Error('SKU_REQUIRED');
  }
  const specCombos = skus.map(s => s.specCombo);
  if (new Set(specCombos).size !== specCombos.length) {
    throw new Error('SKU_SPEC_DUPLICATE');
  }
  for (const sku of skus) {
    if (!sku.specCombo || sku.price === undefined || sku.price === null || sku.stock === undefined || sku.stock === null) {
      throw new Error('SKU_INVALID');
    }
    if (parseFloat(sku.price) < 0) throw new Error('SKU_PRICE_INVALID');
    if (parseInt(sku.stock) < 0) throw new Error('SKU_STOCK_INVALID');
  }

  const conn = await db.beginTransaction();
  try {
    // 创建商品
    const [prodResult] = await conn.execute(
      "INSERT INTO products (shop_id, category_id, title, description, main_image, status) VALUES (?, ?, ?, ?, ?, 'pending_review')",
      [shopId, catId, title, description || '', mainImage || '']
    );
    const productId = prodResult.insertId;

    // 创建 SKU
    for (const sku of skus) {
      await conn.execute(
        'INSERT INTO skus (product_id, spec_combo, price, stock, image) VALUES (?, ?, ?, ?, ?)',
        [productId, sku.specCombo, parseFloat(sku.price), parseInt(sku.stock), sku.image || '']
      );
    }

    // 创建快照
    const snapshot = {
      shop_id: shopId,
      category_id: catId,
      title,
      description: description || '',
      main_image: mainImage || '',
      skus: skus.map(s => ({
        spec_combo: s.specCombo,
        price: parseFloat(s.price),
        stock: parseInt(s.stock),
        image: s.image || ''
      }))
    };
    await conn.execute(
      'INSERT INTO product_snapshots (product_id, snapshot, version) VALUES (?, ?, 1)',
      [productId, JSON.stringify(snapshot)]
    );

    await db.commit(conn);
    return { productId };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 商家 — 更新商品
 * 事务：更新字段 + 重建 SKU + 新快照版本，状态重置为 pending_review
 */
async function updateProduct(productId, shopId, { categoryId, title, description, mainImage, skus }) {
  const id = parseInt(productId) || 0;
  const prodRows = await db.query(
    'SELECT id, shop_id, status FROM products WHERE id = ?',
    [id]
  );
  if (!prodRows.length) throw new Error('PRODUCT_NOT_FOUND');
  if (prodRows[0].shop_id !== shopId) throw new Error('NOT_PRODUCT_OWNER');
  if (!['draft', 'rejected'].includes(prodRows[0].status)) {
    throw new Error('PRODUCT_STATUS_NOT_EDITABLE');
  }

  if (categoryId !== undefined) {
    const catId = parseInt(categoryId) || 0;
    const catRows = await db.query(
      "SELECT id FROM categories WHERE id = ? AND status = 'active'",
      [catId]
    );
    if (!catRows.length) throw new Error('CATEGORY_INVALID');
  }

  if (skus !== undefined) {
    if (!Array.isArray(skus) || !skus.length) throw new Error('SKU_REQUIRED');
    const specCombos = skus.map(s => s.specCombo);
    if (new Set(specCombos).size !== specCombos.length) throw new Error('SKU_SPEC_DUPLICATE');
    for (const sku of skus) {
      if (!sku.specCombo || sku.price === undefined || sku.price === null || sku.stock === undefined || sku.stock === null) {
        throw new Error('SKU_INVALID');
      }
      if (parseFloat(sku.price) < 0) throw new Error('SKU_PRICE_INVALID');
      if (parseInt(sku.stock) < 0) throw new Error('SKU_STOCK_INVALID');
    }
  }

  const conn = await db.beginTransaction();
  try {
    // 构建 UPDATE SET 子句
    const setClauses = [];
    const setParams = [];

    if (title !== undefined) {
      setClauses.push('title = ?');
      setParams.push(title);
    }
    if (description !== undefined) {
      setClauses.push('description = ?');
      setParams.push(description);
    }
    if (mainImage !== undefined) {
      setClauses.push('main_image = ?');
      setParams.push(mainImage);
    }
    if (categoryId !== undefined) {
      setClauses.push('category_id = ?');
      setParams.push(parseInt(categoryId));
    }
    setClauses.push("status = 'pending_review'");

    setParams.push(id);
    await conn.execute(
      `UPDATE products SET ${setClauses.join(', ')} WHERE id = ?`,
      setParams
    );

    // 重建 SKU（如果提供）
    if (skus !== undefined) {
      await conn.execute('DELETE FROM skus WHERE product_id = ?', [id]);
      for (const sku of skus) {
        await conn.execute(
          'INSERT INTO skus (product_id, spec_combo, price, stock, image) VALUES (?, ?, ?, ?, ?)',
          [id, sku.specCombo, parseFloat(sku.price), parseInt(sku.stock), sku.image || '']
        );
      }
    }

    // 获取当前最新版本号并创建快照
    const [snapRows] = await conn.execute(
      'SELECT version FROM product_snapshots WHERE product_id = ? ORDER BY version DESC LIMIT 1',
      [id]
    );
    const newVersion = snapRows.length ? snapRows[0].version + 1 : 1;

    // 查询商品当前状态作为快照
    const [snapProduct] = await conn.execute(
      'SELECT shop_id, category_id, title, description, main_image FROM products WHERE id = ?',
      [id]
    );
    const [snapSkus] = await conn.execute(
      'SELECT spec_combo, price, stock, image FROM skus WHERE product_id = ?',
      [id]
    );

    const snapshot = {
      shop_id: snapProduct[0].shop_id,
      category_id: snapProduct[0].category_id,
      title: snapProduct[0].title,
      description: snapProduct[0].description,
      main_image: snapProduct[0].main_image,
      skus: snapSkus
    };
    await conn.execute(
      'INSERT INTO product_snapshots (product_id, snapshot, version) VALUES (?, ?, ?)',
      [id, JSON.stringify(snapshot), newVersion]
    );

    await db.commit(conn);
    await cacheDel(CACHE_PRODUCT_DETAIL + id);
    return { success: true };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 商家 — 上架商品
 * 仅 approved 状态可上架，成功后清缓存
 */
async function listProduct(productId, shopId) {
  const id = parseInt(productId) || 0;
  const rows = await db.query(
    'SELECT id, shop_id, status FROM products WHERE id = ?',
    [id]
  );
  if (!rows.length) throw new Error('PRODUCT_NOT_FOUND');
  if (rows[0].shop_id !== shopId) throw new Error('NOT_PRODUCT_OWNER');
  if (rows[0].status !== 'approved') throw new Error('PRODUCT_NOT_APPROVED');

  await db.query("UPDATE products SET status = 'listed' WHERE id = ?", [id]);
  await cacheDel(CACHE_PRODUCT_DETAIL + id);
  return { success: true };
}

/**
 * 商家 — 下架商品
 * 仅 listed 状态可下架
 */
async function delistProduct(productId, shopId) {
  const id = parseInt(productId) || 0;
  const rows = await db.query(
    'SELECT id, shop_id, status FROM products WHERE id = ?',
    [id]
  );
  if (!rows.length) throw new Error('PRODUCT_NOT_FOUND');
  if (rows[0].shop_id !== shopId) throw new Error('NOT_PRODUCT_OWNER');
  if (rows[0].status !== 'listed') throw new Error('PRODUCT_NOT_LISTED');

  await db.query("UPDATE products SET status = 'delisted' WHERE id = ?", [id]);
  await cacheDel(CACHE_PRODUCT_DETAIL + id);
  return { success: true };
}

/**
 * 管理员 — 获取商品审核列表
 * 默认筛选 pending_review 状态
 */
async function getAdminProducts({ status, page, pageSize }) {
  const p = parseInt(page) || 1;
  const ps = Math.min(parseInt(pageSize) || 20, 100);
  const offset = (p - 1) * ps;

  const targetStatus = status || 'pending_review';

  const countResult = await db.query(
    'SELECT COUNT(*) as total FROM products WHERE status = ?',
    [targetStatus]
  );
  const total = countResult[0].total;

  const list = await db.query(
    `SELECT p.id, p.title, p.main_image, p.status, p.category_id, p.created_at,
            sh.name AS shop_name
     FROM products p
     JOIN shops sh ON p.shop_id = sh.id
     WHERE p.status = ?
     ORDER BY p.created_at ASC
     LIMIT ? OFFSET ?`,
    [targetStatus, ps, offset]
  );

  return { list, total, page: p, pageSize: ps };
}

/**
 * 管理员 — 获取商品审核详情
 * 含 SKU、快照历史、审核日志
 */
async function getAdminProductDetail(productId) {
  const id = parseInt(productId) || 0;
  const prodRows = await db.query(
    `SELECT p.*, sh.name AS shop_name, c.name AS category_name
     FROM products p
     JOIN shops sh ON p.shop_id = sh.id
     LEFT JOIN categories c ON p.category_id = c.id
     WHERE p.id = ?`,
    [id]
  );
  if (!prodRows.length) throw new Error('PRODUCT_NOT_FOUND');

  const skuRows = await db.query(
    'SELECT id, spec_combo, price, stock, image FROM skus WHERE product_id = ?',
    [id]
  );

  const snapshots = await db.query(
    'SELECT id, version, snapshot, created_at FROM product_snapshots WHERE product_id = ? ORDER BY version DESC',
    [id]
  );

  const auditLogs = await db.query(
    'SELECT id, auditor_id, result, reason, created_at FROM audit_logs WHERE product_id = ? ORDER BY created_at DESC',
    [id]
  );

  return {
    product: {
      id: prodRows[0].id,
      shop_id: prodRows[0].shop_id,
      category_id: prodRows[0].category_id,
      title: prodRows[0].title,
      description: prodRows[0].description,
      status: prodRows[0].status,
      main_image: prodRows[0].main_image,
      created_at: prodRows[0].created_at,
      updated_at: prodRows[0].updated_at,
      shop_name: prodRows[0].shop_name,
      category_name: prodRows[0].category_name
    },
    skus: skuRows.map(s => ({
      id: s.id,
      specCombo: s.spec_combo,
      price: String(s.price),
      stock: s.stock,
      image: s.image
    })),
    snapshots,
    auditLogs
  };
}

/**
 * 管理员 — 审核商品
 * 乐观锁：仅 pending_review 状态可审核
 */
async function reviewProduct(productId, auditorId, { result, reason }) {
  if (!['approved', 'rejected'].includes(result)) {
    throw new Error('INVALID_REVIEW_RESULT');
  }

  const id = parseInt(productId) || 0;
  const prodRows = await db.query(
    'SELECT id, status FROM products WHERE id = ?',
    [id]
  );
  if (!prodRows.length) throw new Error('PRODUCT_NOT_FOUND');
  if (prodRows[0].status !== 'pending_review') throw new Error('ALREADY_REVIEWED');

  const conn = await db.beginTransaction();
  try {
    const [updateResult] = await conn.execute(
      "UPDATE products SET status = ? WHERE id = ? AND status = 'pending_review'",
      [result, id]
    );
    if (!updateResult.affectedRows) {
      await db.rollback(conn);
      throw new Error('ALREADY_REVIEWED');
    }

    await conn.execute(
      'INSERT INTO audit_logs (product_id, auditor_id, result, reason) VALUES (?, ?, ?, ?)',
      [id, auditorId, result, reason || null]
    );

    await db.commit(conn);
    await cacheDel(CACHE_PRODUCT_DETAIL + id);
    return { success: true, result };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = {
  listProducts,
  getProductDetail,
  getMerchantProducts,
  getMerchantProductDetail,
  createProduct,
  updateProduct,
  listProduct,
  delistProduct,
  getAdminProducts,
  getAdminProductDetail,
  reviewProduct
};

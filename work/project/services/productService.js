const db = require('../config/db');

/** 排序方式 → SQL ORDER BY 映射 */
const SORT_MAP = {
  default: 'spu.sales DESC',
  sales: 'spu.sales DESC',
  price_asc: 'min_price ASC',
  price_desc: 'min_price DESC',
  sales_desc: 'spu.sales DESC',
  newest: 'spu.created_at DESC'
};

/**
 * 商品浏览与搜索
 * — ES 搜索降级为 MySQL LIKE（NFR）
 * — 仅返回 status='listed' 且 shop.status='open' 的商品
 * — 参数化查询防 SQL 注入
 *
 * @param {string} q - 搜索关键词（可选）
 * @param {number} cat - 类目ID（可选）
 * @param {string} sort - 排序方式
 * @param {number} page - 页码
 * @param {number} pageSize - 每页条数
 * @returns {{ list: array, total: number, page: number, pageSize: number }}
 */
async function browseProducts(q, cat, sort, page, pageSize) {
  // Step 1: 校验 q 长度 ≤ 200
  if (q && q.length > 128) {
    throw new Error('INVALID_KEYWORD_LENGTH');
  }
  if (!SORT_MAP[sort]) {
    throw new Error('INVALID_SORT');
  }

  // Step 2: 构建动态 WHERE 条件（全参数化，防 SQL 注入）
  const conditions = ['spu.status = ?', 'shops.status = ?'];
  const params = ['listed', 'open'];

  if (q) {
    // MySQL LIKE 降级（ES 不可用时；NFR: ES搜索降级MySQL LIKE）
    conditions.push('spu.name LIKE ?');
    params.push(`%${q}%`);
  }
  if (cat) {
    conditions.push('spu.category_id = ?');
    params.push(cat);
  }

  const whereClause = `WHERE ${conditions.join(' AND ')}`;
  const orderClause = `ORDER BY ${SORT_MAP[sort]}`;
  const offset = (page - 1) * pageSize;

  // Step 3: COUNT 查询 — 获取总条数
  const countSql = `
    SELECT COUNT(DISTINCT spu.id) AS total
    FROM spu
    JOIN shops ON spu.shop_id = shops.id
    LEFT JOIN sku ON sku.spu_id = spu.id
    ${whereClause}
  `;
  const countRows = await db.query(countSql, params);
  const total = countRows[0].total;

  // The count query uses the same params (no pageSize/offset) so no need to duplicate
  // Step 4: 商品列表查询 — JOIN shops + sku 最低价，分页
  const listSql = `
    SELECT
      spu.id,
      spu.name,
      spu.default_image,
      spu.sales,
      spu.shop_id,
      shops.name AS shop_name,
      MIN(sku.price) AS min_price
    FROM spu
    JOIN shops ON spu.shop_id = shops.id
    LEFT JOIN sku ON sku.spu_id = spu.id
    ${whereClause}
    GROUP BY spu.id
    ${orderClause}
    LIMIT ? OFFSET ?
  `;
  const listParams = [...params, pageSize, offset];
  const list = await db.query(listSql, listParams);

  return { list, total, page, pageSize };
}

/**
 * 获取类目树
 * 从 categories 表全量读取，按 level ASC, sort ASC 排序，递归组装为树形结构
 *
 * @returns {array} 树形类目 — [{ id, parentId, name, level, icon, children[] }]
 */
async function getCategoryTree() {
  const rows = await db.query(
    'SELECT id, parent_id, name, level, sort, icon FROM categories ORDER BY level ASC, sort ASC'
  );

  // 递归构建树形结构
  function buildTree(parentId) {
    const children = rows.filter(r => r.parent_id === parentId);
    return children.map(item => ({
      id: item.id,
      parentId: item.parent_id,
      name: item.name,
      level: item.level,
      icon: item.icon,
      children: buildTree(item.id)
    }));
  }

  return buildTree(null);
}

/**
 * 商品详情查询
 * 按序查询 SPU → SKU（含库存）→ 轮播图 → 店铺，任一步失败抛出明确错误
 *
 * @param {number} productId - SPU ID
 * @returns {{ spu: object, skus: array, images: array, shop: object }}
 */
async function getProductDetail(productId) {
  const id = parseInt(productId, 10);
  if (!id || id <= 0) {
    throw new Error('INVALID_PRODUCT_ID');
  }

  // Step 1: 查询 SPU — 仅已上架商品
  const spuRows = await db.query(
    `SELECT id, shop_id, category_id, name, description, default_image, status, sales, created_at
     FROM spu WHERE id = ? AND status = ?`,
    [id, 'listed']
  );
  if (!spuRows.length) {
    throw new Error('PRODUCT_NOT_FOUND');
  }
  const spu = spuRows[0];

  // Step 2: 查询 SKU 列表
  const skuRows = await db.query(
    'SELECT id, spu_id, spec_name, price, image FROM sku WHERE spu_id = ?',
    [id]
  );
  if (!skuRows.length) {
    throw new Error('SKU_NOT_FOUND');
  }

  // Step 3: 查询库存 — 按 sku_id IN (?) AND shop_id=?
  const skuIds = skuRows.map(s => s.id);
  const invRows = await db.query(
    'SELECT sku_id, stock FROM inventories WHERE sku_id IN (?) AND shop_id = ?',
    [skuIds, spu.shop_id]
  );
  const stockMap = {};
  invRows.forEach(r => { stockMap[r.sku_id] = r.stock; });
  const skus = skuRows.map(row => ({
    id: row.id,
    spec_name: row.spec_name,
    price: row.price,
    image: row.image,
    stock: stockMap[row.id] || 0
  }));

  // Step 3: 查询轮播图 — 按 sort 升序排列
  const imageRows = await db.query(
    'SELECT url FROM product_images WHERE spu_id = ? ORDER BY sort ASC',
    [id]
  );
  const images = imageRows.map(row => ({ url: row.url }));

  // Step 4: 查询店铺信息 — 校验店铺存在
  const shopRows = await db.query(
    'SELECT id, name, logo, banner, description, status FROM shops WHERE id = ?',
    [spu.shop_id]
  );
  if (!shopRows.length) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopRow = shopRows[0];
  const shop = {
    id: shopRow.id,
    name: shopRow.name,
    logo: shopRow.logo,
    banner: shopRow.banner,
    description: shopRow.description,
    status: shopRow.status
  };

  return { spu, skus, images, shop };
}

/**
 * 按 ID 查询店铺信息
 * 用于商详页店铺卡片
 *
 * @param {number} shopId - 店铺ID
 * @returns {object} — { id, name, logo, banner, description, status }
 */
async function getShopById(shopId) {
  const rows = await db.query(
    'SELECT id, name, logo, banner, description, status FROM shops WHERE id = ?',
    [shopId]
  );
  if (!rows.length) {
    throw new Error('SHOP_NOT_FOUND');
  }
  return rows[0];
}

module.exports = {
  browseProducts,
  getCategoryTree,
  getProductDetail,
  getShopById
};

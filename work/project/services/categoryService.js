const db = require('../config/db');
const redis = require('../config/redis');

const CACHE_KEY = 'category:tree';
const CACHE_TTL = 3600;

/**
 * Build a nested tree from flat category rows
 * @param {Array} rows - flat rows with id, parent_id
 * @returns {Array} root nodes with children
 */
function buildTree(rows) {
  const map = {};
  const roots = [];

  for (const row of rows) {
    map[row.id] = { ...row, children: [] };
  }

  for (const row of rows) {
    const node = map[row.id];
    if (row.parent_id && row.parent_id !== 0 && map[row.parent_id]) {
      map[row.parent_id].children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

/**
 * Recursively format tree nodes for API response
 * @param {Array} nodes
 * @param {boolean} isAdmin - include sort & status
 * @returns {Array}
 */
function formatTree(nodes, isAdmin) {
  return nodes.map(node => {
    const item = {
      id: node.id,
      name: node.name,
      parentId: node.parent_id,
      children: node.children ? formatTree(node.children, isAdmin) : []
    };
    if (isAdmin) {
      item.sort = node.sort;
      item.status = node.status;
    }
    return item;
  });
}

/**
 * Recursively strip admin fields from cached tree
 */
function stripAdminFields(nodes) {
  return nodes.map(node => ({
    id: node.id,
    name: node.name,
    parentId: node.parentId,
    children: node.children ? stripAdminFields(node.children) : []
  }));
}

/**
 * Invalidate the cached category tree
 */
async function invalidateCache() {
  try {
    await redis.del(CACHE_KEY);
  } catch (e) {
    // Redis down is non-critical; data remains correct from DB
  }
}

/**
 * Get full category tree, optionally with admin fields
 * @param {boolean} isAdmin
 * @returns {Promise<Array>}
 */
async function getCategoryTree(isAdmin = false) {
  // Try cache first
  try {
    const cached = await redis.get(CACHE_KEY);
    if (cached) {
      const tree = JSON.parse(cached);
      return isAdmin ? tree : stripAdminFields(tree);
    }
  } catch (e) {
    // Cache miss → fall through to DB
  }

  const rows = await db.query(
    'SELECT id, name, parent_id, sort, status FROM categories ORDER BY sort ASC, id ASC'
  );

  const tree = buildTree(rows);
  const formatted = formatTree(tree, true);

  // Cache full admin tree
  try {
    await redis.set(CACHE_KEY, JSON.stringify(formatted));
    await redis.expire(CACHE_KEY, CACHE_TTL);
  } catch (e) {
    // Non-critical
  }

  return isAdmin ? formatted : stripAdminFields(formatted);
}

/**
 * Create a new category
 * @param {Object} data - { name, parentId, sort }
 * @returns {Promise<Object>} { id }
 */
async function createCategory(data) {
  const { name, parentId, sort } = data;

  if (!name || typeof name !== 'string' || name.trim().length === 0) {
    throw new Error('INVALID_NAME');
  }
  if (name.trim().length > 50) {
    throw new Error('NAME_TOO_LONG');
  }

  const trimmedName = name.trim();
  const parentIdNum = parseInt(parentId) || 0;
  const sortNum = parseInt(sort) || 0;

  // Validate parent exists
  if (parentIdNum > 0) {
    const parents = await db.query('SELECT id FROM categories WHERE id = ?', [parentIdNum]);
    if (!parents.length) {
      throw new Error('PARENT_NOT_FOUND');
    }
  }

  const result = await db.query(
    'INSERT INTO categories (name, parent_id, sort) VALUES (?, ?, ?)',
    [trimmedName, parentIdNum, sortNum]
  );

  await invalidateCache();

  return { id: result.insertId };
}

/**
 * Update a category
 * @param {number} id
 * @param {Object} data - { name, sort, status }
 */
async function updateCategory(id, data) {
  const idNum = parseInt(id);
  if (!idNum || idNum <= 0) {
    throw new Error('INVALID_ID');
  }

  const rows = await db.query('SELECT id FROM categories WHERE id = ?', [idNum]);
  if (!rows.length) {
    throw new Error('NOT_FOUND');
  }

  const updates = [];
  const params = [];

  if (data.name !== undefined) {
    const trimmedName = (data.name || '').trim();
    if (!trimmedName) {
      throw new Error('INVALID_NAME');
    }
    if (trimmedName.length > 50) {
      throw new Error('NAME_TOO_LONG');
    }
    updates.push('name = ?');
    params.push(trimmedName);
  }

  if (data.sort !== undefined) {
    updates.push('sort = ?');
    params.push(parseInt(data.sort) || 0);
  }

  if (data.status !== undefined) {
    if (!['active', 'disabled'].includes(data.status)) {
      throw new Error('INVALID_STATUS');
    }
    updates.push('status = ?');
    params.push(data.status);
  }

  if (!updates.length) {
    throw new Error('NO_FIELDS_TO_UPDATE');
  }

  params.push(idNum);
  await db.query(`UPDATE categories SET ${updates.join(', ')} WHERE id = ?`, params);

  await invalidateCache();
}

/**
 * Delete a category (rejects if it has children or products)
 * @param {number} id
 */
async function deleteCategory(id) {
  const idNum = parseInt(id);
  if (!idNum || idNum <= 0) {
    throw new Error('INVALID_ID');
  }

  const rows = await db.query('SELECT id FROM categories WHERE id = ?', [idNum]);
  if (!rows.length) {
    throw new Error('NOT_FOUND');
  }

  // Block if sub-categories exist
  const children = await db.query(
    'SELECT COUNT(*) AS cnt FROM categories WHERE parent_id = ?',
    [idNum]
  );
  if (children[0].cnt > 0) {
    throw new Error('HAS_CHILDREN');
  }

  // Block if products reference this category
  const products = await db.query(
    'SELECT COUNT(*) AS cnt FROM products WHERE category_id = ?',
    [idNum]
  );
  if (products[0].cnt > 0) {
    throw new Error('HAS_PRODUCTS');
  }

  await db.query('DELETE FROM categories WHERE id = ?', [idNum]);

  await invalidateCache();
}

module.exports = {
  getCategoryTree,
  createCategory,
  updateCategory,
  deleteCategory
};

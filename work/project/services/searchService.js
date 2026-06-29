const db = require('../config/db');
const logger = require('../config/logger');

const MAX_PAGE_SIZE = 100;
const DEFAULT_PAGE_SIZE = 20;
const ES_RETRY_MAX = 2;
const ES_RETRY_DELAY_MS = 500;

// ========== ES 客户端（可选） ==========
let esClient = null;
try {
  if (process.env.ELASTICSEARCH_HOST) {
    const { Client } = require('@elastic/elasticsearch');
    esClient = new Client({
      node: process.env.ELASTICSEARCH_HOST,
      requestTimeout: 5000
    });
  }
} catch (e) {
  logger.warn('Elasticsearch 客户端未安装或未配置，搜索将使用 MySQL 降级方案');
}

// ========== 工具函数 ==========

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/** 校验并标准化分页参数 */
function normalizePagination(page, pageSize) {
  const p = parseInt(page) || 1;
  const ps = parseInt(pageSize) || DEFAULT_PAGE_SIZE;
  return {
    page: Math.max(1, p),
    pageSize: Math.min(Math.max(1, ps), MAX_PAGE_SIZE),
    offset: (Math.max(1, p) - 1) * Math.min(Math.max(1, ps), MAX_PAGE_SIZE)
  };
}

/** 白名单排序映射 */
const SORT_WHITELIST = {
  '': 'p.created_at DESC',
  'default': 'p.created_at DESC',
  'newest': 'p.created_at DESC',
  'price_asc': 'min_price ASC',
  'price_desc': 'min_price DESC'
};

function getOrderClause(sort) {
  return SORT_WHITELIST[sort] || 'p.created_at DESC';
}

// ========== ES 搜索 ==========

/** 带重试的 ES 搜索，失败抛 ES_UNAVAILABLE */
async function searchWithES(query, filters, offset, pageSize, sort) {
  let lastError;

  for (let attempt = 0; attempt <= ES_RETRY_MAX; attempt++) {
    try {
      const mustClauses = [];
      if (query) {
        mustClauses.push({ match: { title: { query, operator: 'and' } } });
      }

      const filterClauses = [{ term: { status: 'listed' } }];
      if (filters.categoryId) {
        filterClauses.push({ term: { category_id: filters.categoryId } });
      }
      if (filters.priceMin !== undefined || filters.priceMax !== undefined) {
        const range = {};
        if (filters.priceMin !== undefined) range.gte = filters.priceMin;
        if (filters.priceMax !== undefined) range.lte = filters.priceMax;
        filterClauses.push({ range: { min_price: range } });
      }

      const esSort = [];
      if (sort === 'price_asc') esSort.push({ min_price: 'asc' });
      else if (sort === 'price_desc') esSort.push({ min_price: 'desc' });
      else esSort.push({ created_at: 'desc' });

      const body = {
        query: {
          bool: {
            must: mustClauses.length > 0 ? mustClauses : [{ match_all: {} }],
            filter: filterClauses
          }
        },
        from: offset,
        size: pageSize,
        sort: esSort
      };

      const response = await esClient.search({ index: 'products', body });

      const hits = response.hits || {};
      const total = typeof hits.total === 'object' ? hits.total.value : (hits.total || 0);
      const products = (hits.hits || []).map(h => ({
        id: h._source.id,
        title: h._source.title,
        mainImage: h._source.main_image || '',
        minPrice: h._source.min_price != null ? String(h._source.min_price) : '0',
        shopName: h._source.shop_name || ''
      }));

      return { products, total };
    } catch (e) {
      lastError = e;
      if (attempt < ES_RETRY_MAX) {
        await sleep(ES_RETRY_DELAY_MS * (attempt + 1));
      }
    }
  }

  logger.warn('ES 搜索在 %d 次重试后仍失败: %s', ES_RETRY_MAX + 1, lastError.message);
  throw new Error('ES_UNAVAILABLE');
}

// ========== MySQL 降级搜索 ==========

/** MySQL LIKE 搜索（ES 不可用时的降级方案） */
async function searchWithMySQL(query, filters, offset, pageSize, sort) {
  const orderClause = getOrderClause(sort);
  const likePattern = `%${query}%`;

  const whereParts = ['p.status = ?'];
  const params = ['listed'];

  if (query) {
    whereParts.push('p.title LIKE ?');
    params.push(likePattern);
  }
  if (filters.categoryId) {
    whereParts.push('p.category_id = ?');
    params.push(filters.categoryId);
  }

  const whereClause = whereParts.join(' AND ');

  // HAVING 条件（价格筛选基于聚合值）
  const havingParts = [];
  if (filters.priceMin !== undefined) {
    havingParts.push('min_price >= ?');
    params.push(filters.priceMin);
  }
  if (filters.priceMax !== undefined) {
    havingParts.push('min_price <= ?');
    params.push(filters.priceMax);
  }
  const havingClause = havingParts.length > 0 ? 'HAVING ' + havingParts.join(' AND ') : '';

  // 计数查询
  const countSql = `
    SELECT COUNT(DISTINCT p.id) AS total
    FROM products p
    LEFT JOIN skus sk ON p.id = sk.product_id
    WHERE ${whereClause}
    ${havingClause}
  `;
  const countRows = await db.query(countSql, params);
  const total = countRows[0] ? countRows[0].total : 0;

  // 数据查询
  const dataSql = `
    SELECT
      p.id,
      p.title,
      p.main_image,
      sh.name AS shop_name,
      COALESCE(MIN(sk.price), 0) AS min_price
    FROM products p
    JOIN shops sh ON p.shop_id = sh.id
    LEFT JOIN skus sk ON p.id = sk.product_id
    WHERE ${whereClause}
    GROUP BY p.id, p.title, p.main_image, sh.name
    ${havingClause}
    ${orderClause}
    LIMIT ? OFFSET ?
  `;
  const dataParams = [...params, pageSize, offset];
  const rows = await db.query(dataSql, dataParams);

  const products = rows.map(r => ({
    id: r.id,
    title: r.title,
    mainImage: r.main_image || '',
    minPrice: r.min_price != null ? String(r.min_price) : '0',
    shopName: r.shop_name || ''
  }));

  return { products, total };
}

// ========== 搜索日志 ==========

/**
 * 异步记录搜索日志（fire-and-forget，不影响搜索结果返回）
 */
async function recordSearchLog(query, filters, resultCount, userId) {
  try {
    await db.query(
      `INSERT INTO search_logs (user_id, query, filters, result_count)
       VALUES (?, ?, ?, ?)`,
      [
        userId || null,
        query || '',
        filters && Object.keys(filters).length > 0 ? JSON.stringify(filters) : null,
        resultCount
      ]
    );
  } catch (e) {
    logger.warn('搜索日志记录失败: %s', e.message);
  }
}

// ========== 公开接口 ==========

/**
 * 商品全文检索
 * @param {string} query - 搜索关键词
 * @param {object} filters - 筛选条件 { categoryId?, priceMin?, priceMax? }
 * @param {number|string} page - 页码
 * @param {number|string} pageSize - 每页条数
 * @param {string} sort - 排序方式
 * @returns {{ products: Array<{id,title,mainImage,minPrice,shopName}>, total: number }}
 */
async function searchProducts(query, filters = {}, page, pageSize, sort) {
  const { pageSize: ps, offset } = normalizePagination(page, pageSize);
  const q = (query || '').trim();

  let result;

  // 优先使用 ES
  if (esClient && process.env.ELASTICSEARCH_HOST) {
    try {
      result = await searchWithES(q, filters, offset, ps, sort);
    } catch (e) {
      if (e.message === 'ES_UNAVAILABLE') {
        logger.warn('ES 不可用，降级到 MySQL 搜索');
        result = await searchWithMySQL(q, filters, offset, ps, sort);
      } else {
        throw e;
      }
    }
  } else {
    result = await searchWithMySQL(q, filters, offset, ps, sort);
  }

  // 异步记录搜索日志（不阻塞响应）
  recordSearchLog(q, filters, result.total, null).catch(() => {});

  return result;
}

/**
 * 搜索联想建议
 * @param {string} query - 用户输入
 * @param {number|null} userId - 用户ID（可选，用于历史记录）
 * @returns {Array<{ text: string, type: 'hot'|'history'|'suggestion' }>}
 */
async function getSuggestions(query, userId) {
  const q = (query || '').trim();
  const suggestions = [];
  const seen = new Set();

  // 1. 热门搜索（近7天搜索最多的词）
  try {
    const hotRows = await db.query(
      `SELECT query, COUNT(*) AS cnt
       FROM search_logs
       WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
       GROUP BY query
       ORDER BY cnt DESC
       LIMIT 5`
    );
    for (const r of hotRows) {
      if (!seen.has(r.query)) {
        seen.add(r.query);
        suggestions.push({ text: r.query, type: 'hot' });
      }
    }
  } catch (e) {
    logger.warn('获取热门搜索失败: %s', e.message);
  }

  // 2. 用户搜索历史（如果已登录）
  if (userId) {
    try {
      const historyRows = await db.query(
        `SELECT DISTINCT query
         FROM search_logs
         WHERE user_id = ?
         ORDER BY created_at DESC
         LIMIT 5`,
        [userId]
      );
      for (const r of historyRows) {
        if (!seen.has(r.query)) {
          seen.add(r.query);
          suggestions.push({ text: r.query, type: 'history' });
        }
      }
    } catch (e) {
      logger.warn('获取用户搜索历史失败: %s', e.message);
    }
  }

  // 3. 前缀联想（匹配已有搜索词）
  if (q) {
    try {
      const sugRows = await db.query(
        `SELECT DISTINCT query
         FROM search_logs
         WHERE query LIKE ?
         LIMIT 5`,
        [`${q}%`]
      );
      for (const r of sugRows) {
        if (!seen.has(r.query)) {
          seen.add(r.query);
          suggestions.push({ text: r.query, type: 'suggestion' });
        }
      }
    } catch (e) {
      logger.warn('获取联想建议失败: %s', e.message);
    }
  }

  return suggestions;
}

module.exports = { searchProducts, getSuggestions };

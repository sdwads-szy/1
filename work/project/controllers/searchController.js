const searchService = require('../services/searchService');
const response = require('../utils/response');

/**
 * 商品搜索
 * GET /api/search?q=xxx&categoryId=1&priceMin=10&priceMax=100&sort=price_asc&page=1&pageSize=20
 */
async function search(req, res) {
  try {
    const { q, categoryId, priceMin, priceMax, sort, page, pageSize } = req.query;

    const filters = {};
    if (categoryId !== undefined && categoryId !== '') {
      const cid = parseInt(categoryId);
      if (Number.isFinite(cid) && cid > 0) filters.categoryId = cid;
    }
    if (priceMin !== undefined && priceMin !== '') {
      const pmin = parseFloat(priceMin);
      if (Number.isFinite(pmin) && pmin >= 0) filters.priceMin = pmin;
    }
    if (priceMax !== undefined && priceMax !== '') {
      const pmax = parseFloat(priceMax);
      if (Number.isFinite(pmax) && pmax >= 0) filters.priceMax = pmax;
    }

    // page/pageSize 校验放在 service 层统一处理
    const result = await searchService.searchProducts(
      q || '',
      filters,
      page,
      pageSize,
      sort || ''
    );

    response.success(res, result);
  } catch (e) {
    if (e.message === 'ES_UNAVAILABLE') {
      response.fail(res, '搜索服务暂时不可用，请浏览类目', 503);
    } else {
      response.fail(res, '搜索失败', 500);
    }
  }
}

/**
 * 搜索联想建议
 * GET /api/search/suggestions?q=xxx
 */
async function suggestions(req, res) {
  try {
    const { q } = req.query;
    const userId = req.userId || null;
    const result = await searchService.getSuggestions(q || '', userId);
    response.success(res, result);
  } catch (e) {
    response.fail(res, '获取建议失败', 500);
  }
}

module.exports = { search, suggestions };

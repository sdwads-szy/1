const response = require('../utils/response');
const productService = require('../services/productService');

/**
 * GET /api/products
 * 商品列表：关键词搜索、类目筛选、排序、分页
 */
async function getProducts(req, res) {
  try {
    const q = req.query.q || undefined;
    const cat = req.query.cat ? parseInt(req.query.cat, 10) : undefined;
    const sort = req.query.sort || 'default';
    const page = parseInt(req.query.page, 10) || 1;
    const pageSize = parseInt(req.query.pageSize, 10) || 20;

    // 校验参数
    if (q && q.length > 200) {
      return response.fail(res, '搜索词过长，请精简后重试', 400);
    }
    if (!['default', 'price_asc', 'price_desc', 'sales_desc', 'newest'].includes(sort)) {
      return response.fail(res, '不支持的排序方式', 400);
    }
    if (page < 1) {
      return response.fail(res, '页码必须大于0', 400);
    }
    if (pageSize < 1 || pageSize > 50) {
      return response.fail(res, '每页条数必须在1-50之间', 400);
    }

    const result = await productService.browseProducts(q, cat, sort, page, pageSize);

    response.success(res, {
      list: result.list,
      total: result.total,
      page: result.page,
      pageSize: result.pageSize
    }, '商品列表查询成功');
  } catch (err) {
    if (err.message === 'INVALID_QUERY') {
      return response.fail(res, '搜索词过长，请精简后重试', 400);
    }
    if (err.message === 'INVALID_SORT') {
      return response.fail(res, '不支持的排序方式', 400);
    }
    response.error(res, '服务器内部错误');
  }
}

/**
 * GET /api/products/:id
 * 商品详情：SPU信息、SKU列表（含库存）、轮播图、店铺信息
 */
async function getProductDetail(req, res) {
  try {
    const productId = parseInt(req.params.id, 10);

    if (!productId || productId < 1) {
      return response.fail(res, '商品ID不合法', 400);
    }

    const data = await productService.getProductDetail(productId);

    response.success(res, data, '商品详情查询成功');
  } catch (err) {
    if (err.message === 'PRODUCT_NOT_FOUND') {
      return response.fail(res, '商品不存在或已下架', 404);
    }
    if (err.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    response.error(res, '服务器内部错误');
  }
}

/**
 * GET /api/categories
 * 全量类目树，用于首页分类导航和商品筛选
 */
async function getCategories(req, res) {
  try {
    const tree = await productService.getCategoryTree();
    response.success(res, { tree }, '类目查询成功');
  } catch (err) {
    response.error(res, '服务器内部错误');
  }
}

/**
 * GET /api/shops/:id
 * 店铺信息，用于商详页店铺卡片
 */
async function getShopInfo(req, res) {
  try {
    const shopId = parseInt(req.params.id, 10);

    if (!shopId || shopId < 1) {
      return response.fail(res, '店铺ID不合法', 400);
    }

    const shop = await productService.getShopById(shopId);
    // shop fields: name, logo, banner, description, status
    // frozen shops: returned with status='frozen', no error

    response.success(res, shop, '店铺信息查询成功');
  } catch (err) {
    if (err.message === 'SHOP_NOT_FOUND') {
      return response.fail(res, '店铺不存在', 404);
    }
    response.error(res, '服务器内部错误');
  }
}

module.exports = {
  getProducts,
  getProductDetail,
  getCategories,
  getShopInfo
};

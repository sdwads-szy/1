const categoryService = require('../services/categoryService');
const response = require('../utils/response');

/** Error code → HTTP response mapping */
const ERROR_MAP = {
  'NOT_FOUND':          { code: 404, message: '类目不存在' },
  'HAS_CHILDREN':       { code: 422, message: '该类目下有子类目，无法删除' },
  'HAS_PRODUCTS':       { code: 422, message: '该类目下有商品，无法删除' },
  'PARENT_NOT_FOUND':   { code: 422, message: '父类目不存在' },
  'INVALID_NAME':       { code: 400, message: '类目名称不能为空' },
  'NAME_TOO_LONG':      { code: 400, message: '类目名称不能超过50个字符' },
  'INVALID_STATUS':     { code: 400, message: '无效的状态值' },
  'INVALID_ID':         { code: 400, message: '无效的类目ID' },
  'NO_FIELDS_TO_UPDATE':{ code: 400, message: '没有需要更新的字段' }
};

/**
 * Map a service-layer error to an HTTP response, or fall through to global handler
 */
function handleError(e, res, next) {
  const mapped = ERROR_MAP[e.message];
  if (mapped) {
    return response.fail(res, mapped.message, mapped.code);
  }
  next(e);
}

/**
 * GET /api/categories — Public category tree (excludes sort & status)
 */
async function getCategoryTree(req, res, next) {
  try {
    const tree = await categoryService.getCategoryTree(false);
    response.success(res, tree, '获取类目成功');
  } catch (e) {
    handleError(e, res, next);
  }
}

/**
 * GET /api/admin/categories — Admin category tree (includes sort & status)
 */
async function adminGetCategoryTree(req, res, next) {
  try {
    const tree = await categoryService.getCategoryTree(true);
    response.success(res, tree, '获取类目成功');
  } catch (e) {
    handleError(e, res, next);
  }
}

/**
 * POST /api/admin/categories — Create a category
 */
async function createCategory(req, res, next) {
  try {
    const { name, parentId, sort } = req.body;
    const result = await categoryService.createCategory({ name, parentId, sort });
    response.success(res, result, '创建类目成功');
  } catch (e) {
    handleError(e, res, next);
  }
}

/**
 * PUT /api/admin/categories/:id — Update a category
 */
async function updateCategory(req, res, next) {
  try {
    const { id } = req.params;
    const { name, sort, status } = req.body;
    await categoryService.updateCategory(id, { name, sort, status });
    response.success(res, { success: true }, '更新类目成功');
  } catch (e) {
    handleError(e, res, next);
  }
}

/**
 * DELETE /api/admin/categories/:id — Delete a category
 */
async function deleteCategory(req, res, next) {
  try {
    const { id } = req.params;
    await categoryService.deleteCategory(id);
    response.success(res, { success: true }, '删除类目成功');
  } catch (e) {
    handleError(e, res, next);
  }
}

module.exports = {
  getCategoryTree,
  adminGetCategoryTree,
  createCategory,
  updateCategory,
  deleteCategory
};

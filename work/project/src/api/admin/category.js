import request from '@/utils/request';

// @api 平台后台类目管理 — 3级树形CRUD

/**
 * 获取类目树
 * @returns {Promise<Array>} [{ id, name, parentId, sort, status, children }]
 */
export function getCategoryTree() {
  return request({ url: '/admin/categories', method: 'get' });
}

/**
 * 创建类目
 * @param {Object} data — { name, parentId, sort }
 * @returns {Promise<Object>} { id }
 */
export function createCategory(data) {
  return request({ url: '/admin/categories', method: 'post', data });
}

/**
 * 更新类目
 * @param {number} id — 类目ID
 * @param {Object} data — { name, sort, status }
 * @returns {Promise<Object>} { success }
 */
export function updateCategory(id, data) {
  return request({ url: `/admin/categories/${id}`, method: 'put', data });
}

/**
 * 删除类目
 * @param {number} id — 类目ID
 * @returns {Promise<Object>} { success }
 */
export function deleteCategory(id) {
  return request({ url: `/admin/categories/${id}`, method: 'delete' });
}

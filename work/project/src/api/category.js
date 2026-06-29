import request from '@/utils/request';

/**
 * @api 类目接口：前台获取类目树
 * 返回 [{{ id, name, parentId, children }}] 3级树
 */
export function getCategoryTree() {
  return request({
    url: '/categories',
    method: 'get'
  });
}

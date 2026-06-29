import request from '@/utils/request';

// @api 平台后台-用户管理

/** 获取用户列表 */
export function getUserList(data) {
  return request({
    url: '/admin/users',
    method: 'get',
    params: data
  });
}

/** 封禁用户 */
export function banUser(id) {
  return request({
    url: `/admin/users/${id}/ban`,
    method: 'put'
  });
}

/** 解封用户 */
export function unbanUser(id) {
  return request({
    url: `/admin/users/${id}/unban`,
    method: 'put'
  });
}

/** 分配用户角色 */
export function updateUserRole(id, data) {
  return request({
    url: `/admin/users/${id}/role`,
    method: 'put',
    data
  });
}

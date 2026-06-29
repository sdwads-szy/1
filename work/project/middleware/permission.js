const response = require('../utils/response');

/**
 * 校验当前用户是否拥有指定角色（至少一个）
 * 必须在 authenticate 之后使用（依赖 req.user.role）
 * @param  {...string} roles 允许的角色列表
 * @returns {import('express').RequestHandler}
 */
function hasRole(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return response.unauthorized(res, '请先登录');
    }
    if (!roles.includes(req.user.role)) {
      return response.forbidden(res, '无权访问该资源');
    }
    next();
  };
}

/**
 * 校验当前用户是否拥有指定权限
 * @param {string} permission 权限标识
 * @returns {import('express').RequestHandler}
 */
function hasPermission(permission) {
  return (req, res, next) => {
    if (!req.user) {
      return response.unauthorized(res, '请先登录');
    }
    const permissions = req.user.permissions || [];
    if (!permissions.includes(permission)) {
      return response.forbidden(res, '无权执行该操作');
    }
    next();
  };
}

/**
 * 校验当前用户是否同时拥有所有指定权限
 * @param  {...string} permissions 需要校验的权限列表
 * @returns {import('express').RequestHandler}
 */
function hasAllPermissions(...permissions) {
  return (req, res, next) => {
    if (!req.user) {
      return response.unauthorized(res, '请先登录');
    }
    const userPermissions = req.user.permissions || [];
    const hasAll = permissions.every((p) => userPermissions.includes(p));
    if (!hasAll) {
      return response.forbidden(res, '无权执行该操作');
    }
    next();
  };
}

module.exports = { hasRole, hasPermission, hasAllPermissions };

const response = require('../utils/response');

/**
 * 角色守卫 — 用户角色必须在允许列表中
 * @param  {...string} roles 允许的角色（如 'admin', 'merchant'）
 * @returns {Function} Express 中间件
 */
function hasRole(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return response.unauthorized(res, '请先登录');
    }

    if (!roles.includes(req.user.role)) {
      return response.forbidden(res, '无权访问，角色不足');
    }

    next();
  };
}

/**
 * 权限守卫 — 用户必须拥有指定权限
 * @param {string} permission 权限标识
 * @returns {Function} Express 中间件
 */
function hasPermission(permission) {
  return (req, res, next) => {
    if (!req.user) {
      return response.unauthorized(res, '请先登录');
    }

    const userPermissions = req.user.permissions || [];
    if (!userPermissions.includes(permission)) {
      return response.forbidden(res, `无权访问，缺少权限: ${permission}`);
    }

    next();
  };
}

/**
 * 全权限守卫 — 用户必须拥有所有指定权限
 * @param  {...string} permissions 需要的权限列表
 * @returns {Function} Express 中间件
 */
function hasAllPermissions(...permissions) {
  return (req, res, next) => {
    if (!req.user) {
      return response.unauthorized(res, '请先登录');
    }

    const userPermissions = req.user.permissions || [];
    const missing = permissions.filter(p => !userPermissions.includes(p));

    if (missing.length > 0) {
      return response.forbidden(res, `无权访问，缺少权限: ${missing.join(', ')}`);
    }

    next();
  };
}

module.exports = { hasRole, requireRole: hasRole, hasPermission, hasAllPermissions };

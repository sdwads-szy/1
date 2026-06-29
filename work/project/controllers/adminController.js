const adminService = require('../services/adminService');
const response = require('../utils/response');

/**
 * 错误码 → HTTP 状态码 + 消息映射
 */
const ERROR_MAP = {
  USER_NOT_FOUND:   { code: 404, message: '用户不存在' },
  CANNOT_BAN_SELF:  { code: 422, message: '不能封禁自己' },
  CANNOT_BAN_ADMIN: { code: 403, message: '不能操作管理员账户' },
  INVALID_ROLE:     { code: 400, message: '无效的角色值' },
};

/** 统一错误处理 */
function handleError(res, e) {
  const mapped = ERROR_MAP[e.message];
  if (mapped) {
    return response.fail(res, mapped.message, mapped.code);
  }
  return response.fail(res, e.message || '服务器内部错误', 500);
}

// ==================== 用户管理 ====================

/** GET /admin/users — 用户列表 */
async function listUsers(req, res) {
  try {
    const result = await adminService.listUsers(req.query);
    response.success(res, result);
  } catch (e) {
    handleError(res, e);
  }
}

/** PUT /admin/users/:id/ban — 封禁用户 */
async function banUser(req, res) {
  try {
    const targetId = parseInt(req.params.id) || 0;
    await adminService.banUser(req.userId, targetId);
    response.success(res, null, '用户已封禁');
  } catch (e) {
    handleError(res, e);
  }
}

/** PUT /admin/users/:id/unban — 解封用户 */
async function unbanUser(req, res) {
  try {
    const targetId = parseInt(req.params.id) || 0;
    await adminService.unbanUser(targetId);
    response.success(res, null, '用户已解封');
  } catch (e) {
    handleError(res, e);
  }
}

/** PUT /admin/users/:id/role — 分配角色 */
async function setUserRole(req, res) {
  try {
    const targetId = parseInt(req.params.id) || 0;
    const { role } = req.body;

    if (!role || !['user', 'merchant', 'admin'].includes(role)) {
      return response.fail(res, '无效的角色值，可选: user/merchant/admin', 400);
    }

    await adminService.setUserRole(req.userId, targetId, role);
    response.success(res, null, '角色已更新');
  } catch (e) {
    handleError(res, e);
  }
}

// ==================== 经营报表 ====================

/** GET /admin/reports/orders — 订单报表 */
async function getOrderReport(req, res) {
  try {
    const { startDate, endDate } = req.query;
    const result = await adminService.getOrderReport(startDate, endDate);
    response.success(res, result);
  } catch (e) {
    handleError(res, e);
  }
}

/** GET /admin/reports/payments — 支付报表 */
async function getPaymentReport(req, res) {
  try {
    const { startDate, endDate } = req.query;
    const result = await adminService.getPaymentReport(startDate, endDate);
    response.success(res, result);
  } catch (e) {
    handleError(res, e);
  }
}

/** GET /admin/reports/refunds — 退款报表 */
async function getRefundReport(req, res) {
  try {
    const { startDate, endDate } = req.query;
    const result = await adminService.getRefundReport(startDate, endDate);
    response.success(res, result);
  } catch (e) {
    handleError(res, e);
  }
}

module.exports = {
  listUsers,
  banUser,
  unbanUser,
  setUserRole,
  getOrderReport,
  getPaymentReport,
  getRefundReport,
};

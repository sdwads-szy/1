/**
 * Unified HTTP response helpers.
 *
 * 🛑 Calling convention: response.success(res, data, 'message')
 *    data is the SECOND argument, message is the THIRD.
 *    NEVER swap them.
 */
const response = {
  /**
   * Successful response.
   * @param {import('express').Response} res
   * @param {*} data - Business data payload
   * @param {string} message - Success message
   */
  success(res, data = null, message = '成功') {
    return res.json({ success: true, code: 200, message, data });
  },

  /**
   * Client error response.
   * @param {import('express').Response} res
   * @param {string} message - Error message
   * @param {number} code - HTTP status code (default 400)
   * @param {*} data - Optional error details
   */
  fail(res, message = '失败', code = 400, data = null) {
    return res.status(code).json({ success: false, code, message, data });
  },

  /**
   * 401 Unauthorized.
   * @param {import('express').Response} res
   * @param {string} message
   */
  unauthorized(res, message = '请先登录') {
    return this.fail(res, message, 401);
  },

  /**
   * 403 Forbidden.
   * @param {import('express').Response} res
   * @param {string} message
   */
  forbidden(res, message = '无权访问') {
    return this.fail(res, message, 403);
  },

  /**
   * 404 Not Found.
   * @param {import('express').Response} res
   * @param {string} message
   */
  notFound(res, message = '资源不存在') {
    return this.fail(res, message, 404);
  },

  /**
   * 409 Conflict.
   * @param {import('express').Response} res
   * @param {string} message
   */
  conflict(res, message = '数据冲突') {
    return this.fail(res, message, 409);
  },

  /**
   * 422 Unprocessable Entity (business rule violation).
   * @param {import('express').Response} res
   * @param {string} message
   */
  unprocessable(res, message = '业务规则不满足') {
    return this.fail(res, message, 422);
  },

  /**
   * 500 Internal Server Error.
   * @param {import('express').Response} res
   * @param {string} message
   */
  error(res, message = '服务器错误') {
    return this.fail(res, message, 500);
  }
};

module.exports = response;

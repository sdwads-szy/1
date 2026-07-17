const response = {
  success(res, data = null, message = '成功') {
    return res.json({ success: true, code: 200, message, data });
  },

  fail(res, message = '失败', code = 400, data = null) {
    return res.status(code).json({ success: false, code, message, data });
  },

  unauthorized(res, message = '请先登录') {
    return this.fail(res, message, 401);
  },

  forbidden(res, message = '无权访问') {
    return this.fail(res, message, 403);
  },

  error(res, message = '服务器错误') {
    return this.fail(res, message, 500);
  }
};

module.exports = response;

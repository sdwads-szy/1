const paymentService = require('../services/paymentService');
const response = require('../utils/response');

/**
 * POST /api/payments/:id/pay — 发起支付
 * 调用第三方支付网关生成支付链接/二维码
 */
async function pay(req, res) {
  try {
    const paymentId = parseInt(req.params.id) || 0;
    const { channel } = req.body;

    if (!channel || !['wxpay', 'alipay'].includes(channel)) {
      return response.fail(res, '支付渠道无效，仅支持 wxpay/alipay', 400);
    }

    const result = await paymentService.pay(paymentId, channel, req.userId);
    response.success(res, result, '支付发起成功');
  } catch (e) {
    const errorMap = {
      'NOT_FOUND': [404, '支付记录不存在'],
      'FORBIDDEN': [403, '无权操作该支付'],
      'INVALID_STATUS': [422, '当前支付状态不允许此操作'],
      'ORDER_ALREADY_PAID': [409, '订单已支付'],
      'PAYMENT_TIMEOUT': [408, '支付超时，订单已取消'],
      'GATEWAY_ERROR': [502, '支付网关异常，请稍后重试']
    };

    const [code, message] = errorMap[e.message] || [500, '支付发起失败'];
    response.fail(res, message, code);
  }
}

/**
 * POST /api/payments/callback — 支付网关回调通知
 * 验证签名后更新支付记录和订单状态
 */
async function callback(req, res) {
  try {
    const { tradeNo, orderNo, status, sign } = req.body;

    if (!tradeNo || !orderNo || !status || !sign) {
      return res.json({ code: 'FAIL', message: '缺少必要参数' });
    }

    const result = await paymentService.handleCallback(req.body);
    res.json(result);
  } catch (e) {
    if (e.message === 'INVALID_SIGN') {
      return res.json({ code: 'FAIL', message: '签名验证失败' });
    }
    if (e.message === 'NOT_FOUND') {
      return res.json({ code: 'FAIL', message: '订单不存在' });
    }
    res.json({ code: 'FAIL', message: '系统异常' });
  }
}

/**
 * GET /api/payments/:id/status — 查询支付状态
 */
async function getStatus(req, res) {
  try {
    const paymentId = parseInt(req.params.id) || 0;
    const result = await paymentService.getPaymentStatus(paymentId, req.userId);
    response.success(res, result, '查询成功');
  } catch (e) {
    if (e.message === 'NOT_FOUND') {
      return response.fail(res, '支付记录不存在', 404);
    }
    if (e.message === 'FORBIDDEN') {
      return response.fail(res, '无权操作该支付', 403);
    }
    response.fail(res, '查询失败', 500);
  }
}

module.exports = { pay, callback, getStatus };

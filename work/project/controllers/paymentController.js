const response = require('../utils/response');
const paymentService = require('../services/paymentService');

/**
 * POST /api/payments/pay — 发起支付
 * 输入: { orderNo, channel } — 主订单号 + 支付渠道(wechat/alipay/unionpay)
 * 输出: { paymentUrl, transactionNos[], totalAmount }
 */
async function initiatePayment(req, res) {
  try {
    const { orderNo, channel } = req.body;

    // 参数校验
    if (!orderNo) return response.fail(res, '订单号不能为空', 400);
    if (!channel) return response.fail(res, '支付渠道不能为空', 400);

    const validChannels = ['wechat', 'alipay', 'unionpay'];
    if (!validChannels.includes(channel)) {
      return response.fail(res, '不支持的支付渠道，请选择微信/支付宝/银联', 400);
    }

    const result = await paymentService.pay(req.userId, orderNo, channel);
    response.success(res, result, '支付发起成功');
  } catch (e) {
    const errorMap = {
      'ORDER_NOT_FOUND': [404, '订单不存在'],
      'FORBIDDEN': [403, '无权操作此订单'],
      'ORDER_STATUS_INVALID': [422, '当前订单状态不可支付'],
      'PAYMENT_TIMEOUT': [408, '订单已超时，请重新下单'],
      'DUPLICATE_PAYMENT': [409, '订单已支付'],
    };
    const [code, msg] = errorMap[e.message] || [500, '支付失败'];
    response.fail(res, msg, code);
  }
}

/**
 * GET /api/payments/status/:orderNo — 支付结果轮询
 * 输入: orderNo (URL 参数)
 * 输出: { status: 'pending'|'success'|'failed', orderNo }
 */
async function getStatus(req, res) {
  try {
    const { orderNo } = req.params;

    if (!orderNo) return response.fail(res, '订单号不能为空', 400);

    const result = await paymentService.getPaymentStatus(req.userId, orderNo);
    response.success(res, result, '查询成功');
  } catch (e) {
    const errorMap = {
      'ORDER_NOT_FOUND': [404, '订单不存在'],
      'FORBIDDEN': [403, '无权操作此订单'],
    };
    const [code, msg] = errorMap[e.message] || [500, '查询失败'];
    response.fail(res, msg, code);
  }
}

module.exports = { initiatePayment, getStatus };

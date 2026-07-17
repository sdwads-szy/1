const response = require('../utils/response');
const merchantWithdrawalService = require('../services/merchantWithdrawalService');
const { getWalletByUserId } = require('../services/merchantWalletService');

/**
 * POST /api/merchant/withdrawals
 * 商家提现申请 — amount来自提现金额输入，bankAccount来自银行账户输入(加密传输)
 */
async function submitWithdrawal(req, res) {
  try {
    const { amount, bankAccount } = req.body;

    // 参数校验
    const parsedAmount = parseFloat(amount);
    if (!amount || isNaN(parsedAmount) || parsedAmount < 0.01) {
      return response.fail(res, '提现金额无效，必须大于0.01', 400);
    }
    if (!bankAccount || String(bankAccount).trim() === '') {
      return response.fail(res, '银行账号不能为空', 400);
    }

    // 通过 userId 获取钱包 → merchant_id
    const wallet = await getWalletByUserId(req.userId);
    if (!wallet) {
      return response.fail(res, '钱包不存在', 404);
    }

    const result = await merchantWithdrawalService.submitWithdrawal(
      wallet.merchant_id,
      parsedAmount,
      String(bankAccount).trim()
    );

    return response.success(res, result, '提现申请已提交');
  } catch (e) {
    const errorMap = {
      'WALLET_NOT_FOUND': [404, '钱包不存在'],
      'INSUFFICIENT_BALANCE': [422, '余额不足'],
      'BALANCE_CHANGED': [409, '余额已变动，请刷新重试'],
    };
    if (errorMap[e.message]) {
      const [status, message] = errorMap[e.message];
      return response.fail(res, message, status);
    }
    // INSUFFICIENT_BALANCE — 附带可用余额
    if (e.message === 'INSUFFICIENT_BALANCE') {
      const available = e.availableBalance || 0;
      return response.fail(res, `余额不足，可提余额: ¥${available}`, 422);
    }
    return response.fail(res, '提现申请失败', 500);
  }
}

/**
 * GET /api/merchant/withdrawals
 * 商家查自己的提现记录 — 支持分页 + status筛选
 */
async function getWithdrawals(req, res) {
  try {
    const wallet = await getWalletByUserId(req.userId);
    if (!wallet) {
      return response.fail(res, '钱包不存在', 404);
    }

    const page = parseInt(req.query.page) || 1;
    const pageSize = Math.min(parseInt(req.query.pageSize) || 20, 100);
    const status = req.query.status || null;

    const result = await merchantWithdrawalService.getWithdrawals(
      wallet.merchant_id,
      page,
      pageSize,
      status
    );

    return response.success(res, result);
  } catch (e) {
    return response.fail(res, '获取提现记录失败', 500);
  }
}

module.exports = { submitWithdrawal, getWithdrawals };

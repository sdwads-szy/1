const merchantWalletService = require('../services/merchantWalletService');
const response = require('../utils/response');

/**
 * GET /api/merchant/wallet
 * 商家钱包余额查询
 */
async function getWalletBalance(req, res) {
  try {
    const wallet = await merchantWalletService.getWalletByUserId(req.userId);
    response.success(res, {
      balance: wallet.balance,
      frozenBalance: wallet.frozen_balance,
      totalEarned: wallet.total_earned
    }, '查询成功');
  } catch (e) {
    if (e.message === 'WALLET_NOT_FOUND') {
      response.fail(res, '钱包不存在', 404);
    } else if (e.message === 'FORBIDDEN') {
      response.fail(res, '非商家角色无权访问', 403);
    } else {
      response.error(res, e.message);
    }
  }
}

/**
 * GET /api/merchant/settlements
 * 商家结算单列表（分页）
 */
async function listSettlements(req, res) {
  try {
    const page = Math.max(1, parseInt(req.query.page) || 1);
    const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize) || 20));
    const result = await merchantWalletService.getSettlementsByUserId(req.userId, page, pageSize);
    response.success(res, {
      list: result.list,
      total: result.total,
      page: result.page,
      pageSize: result.pageSize
    }, '查询成功');
  } catch (e) {
    if (e.message === 'WALLET_NOT_FOUND') {
      response.fail(res, '钱包不存在', 404);
    } else if (e.message === 'FORBIDDEN') {
      response.fail(res, '非商家角色无权访问', 403);
    } else {
      response.error(res, e.message);
    }
  }
}

module.exports = { getWalletBalance, listSettlements };

const db = require('../config/db');

/**
 * 按用户ID查商家钱包
 * @param {number} userId - 用户ID（来自auth token）
 * @returns {object} 钱包记录，含 version 用于后续 CAS 更新
 * @throws {Error} WALLET_NOT_FOUND — 商家不存在或钱包未创建
 */
async function getWalletByUserId(userId) {
  // 1. 通过 user_id 查商家ID
  const merchants = await db.query(
    'SELECT id FROM `merchants` WHERE user_id = ?',
    [userId]
  );
  if (!merchants.length) {
    throw new Error('WALLET_NOT_FOUND');
  }
  const merchantId = merchants[0].id;

  // 2. 查钱包（期望使用 idx_merchant_id 索引）
  const wallets = await db.query(
    'SELECT id, merchant_id, balance, frozen_balance, total_earned, version FROM `merchant_wallets` WHERE merchant_id = ?',
    [merchantId]
  );
  if (!wallets.length) {
    throw new Error('WALLET_NOT_FOUND');
  }

  return wallets[0];
}

/**
 * 按用户ID查商家结算单列表（分页）
 * @param {number} userId - 用户ID（来自auth token）
 * @param {number} page - 页码，≥1
 * @param {number} pageSize - 每页条数，1-50
 * @returns {object} { list, total, page, pageSize }
 */
async function getSettlementsByUserId(userId, page = 1, pageSize = 20) {
  // 1. 通过 user_id 查商家ID
  const merchants = await db.query(
    'SELECT id FROM `merchants` WHERE user_id = ?',
    [userId]
  );
  if (!merchants.length) {
    throw new Error('WALLET_NOT_FOUND');
  }
  const merchantId = merchants[0].id;

  const offset = (page - 1) * pageSize;

  // 2. 并行查结算单列表 + 总数（期望使用 idx_merchant_period 索引）
  const [rows, countResult] = await Promise.all([
    db.query(
      'SELECT id, period, amount, status, paid_at, created_at FROM `settlement_orders` WHERE merchant_id = ? ORDER BY period DESC LIMIT ? OFFSET ?',
      [merchantId, pageSize, offset]
    ),
    db.query(
      'SELECT COUNT(*) as total FROM `settlement_orders` WHERE merchant_id = ?',
      [merchantId]
    )
  ]);

  return {
    list: rows,
    total: countResult[0].total,
    page,
    pageSize
  };
}

async function updateWalletBalance(merchantId, amount, conn) {
  const dbClient = conn || db;
  const [result] = await dbClient.execute(
    `UPDATE merchant_wallets
     SET balance = balance + ?, version = version + 1
     WHERE merchant_id = ? AND version = (SELECT v FROM (SELECT version AS v FROM merchant_wallets WHERE merchant_id = ?) AS t)`,
    [amount, merchantId, merchantId]
  );
  if (result.affectedRows === 0) throw new Error('BALANCE_CHANGED');
  return result;
}

async function createWallet(merchantId) {
  await db.query(
    'INSERT INTO merchant_wallets (merchant_id, balance, frozen_balance, total_earned, version) VALUES (?, 0.00, 0.00, 0.00, 0)',
    [merchantId]
  );
}

module.exports = { getWallet: getWalletByUserId, getWalletByUserId, updateWalletBalance, createWallet, getSettlementsByUserId };

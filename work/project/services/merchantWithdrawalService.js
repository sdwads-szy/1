const db = require('../config/db');
const encryption = require('../utils/encryption');

/**
 * 生成提现单号 — WD + 时间戳(36进制) + 随机串(6位)
 */
function generateRequestNo() {
  const ts = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).substring(2, 8).toUpperCase();
  return `WD${ts}${rand}`;
}

/**
 * submitWithdrawal — 提现超额防护 + 乐观锁余额扣减
 *
 * 流程:
 *   1. SELECT balance, version FROM merchant_wallets WHERE merchant_id=?
 *   2. 校验 balance >= amount → 不足抛 INSUFFICIENT_BALANCE(含availableBalance)
 *   3. BEGIN TX: UPDATE 乐观锁扣减(balance-amount, frozen_balance+amount)
 *   4. INSERT withdrawal_requests
 *   5. COMMIT
 *
 * @param {number} merchantId — 商家ID
 * @param {number} amount       — 提现金额
 * @param {string} bankAccount  — 银行账号(明文传入，service内加密)
 * @returns {{requestNo: string, status: 'pending'}}
 */
async function submitWithdrawal(merchantId, amount, bankAccount) {
  // ── Step 1: 查钱包余额 + 版本号 ──
  const walletRows = await db.query(
    'SELECT balance, frozen_balance, version FROM merchant_wallets WHERE merchant_id = ?',
    [merchantId]
  );

  if (!walletRows || walletRows.length === 0) {
    throw new Error('WALLET_NOT_FOUND');
  }

  const wallet = walletRows[0];
  const balance = parseFloat(wallet.balance);
  const version = wallet.version;

  // ── Step 2: 校验余额 >= 提现金额 ──
  if (balance < amount) {
    const err = new Error('INSUFFICIENT_BALANCE');
    err.availableBalance = balance;
    throw err;
  }

  // ── Step 3-5: 事务内乐观锁扣减 + 创建提现申请 ──
  const conn = await db.beginTransaction();
  try {
    const [updateResult] = await conn.execute(
      `UPDATE merchant_wallets
       SET balance = balance - ?,
           frozen_balance = frozen_balance + ?,
           version = version + 1
       WHERE merchant_id = ? AND version = ? AND balance >= ?`,
      [amount, amount, merchantId, version, amount]
    );

    if (updateResult.affectedRows === 0) {
      throw new Error('BALANCE_CHANGED');
    }

    // Step 4: 创建提现申请 — 雪花单号 + 加密银行账号
    const requestNo = generateRequestNo();
    const encryptedBankAccount = encryption.encrypt(bankAccount);

    await conn.execute(
      'INSERT INTO withdrawal_requests (request_no, merchant_id, amount, bank_account) VALUES (?, ?, ?, ?)',
      [requestNo, merchantId, amount, encryptedBankAccount]
    );

    // Step 5: 提交事务
    await db.commit(conn);

    return { requestNo, status: 'pending' };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * getWithdrawals — 商家查自己的提现记录
 *
 * @param {number} merchantId — 商家ID
 * @param {number} page       — 页码 (1-indexed)
 * @param {number} pageSize   — 每页条数
 * @param {string|null} status — 可选状态筛选
 * @returns {{list: array, total: number, page: number, pageSize: number}}
 */
async function getWithdrawals(merchantId, page = 1, pageSize = 20, status = null) {
  const params = [merchantId];
  let whereClause = 'WHERE merchant_id = ?';

  if (status) {
    whereClause += ' AND status = ?';
    params.push(status);
  }

  // 计数
  const countRows = await db.query(
    `SELECT COUNT(*) AS total FROM withdrawal_requests ${whereClause}`,
    params
  );
  const total = countRows[0].total;

  // 分页查询
  const offset = (page - 1) * pageSize;
  const rows = await db.query(
    `SELECT id, request_no, amount, status, review_reason, paid_at, created_at
     FROM withdrawal_requests ${whereClause}
     ORDER BY created_at DESC
     LIMIT ? OFFSET ?`,
    [...params, pageSize, offset]
  );

  return { list: rows, total, page, pageSize };
}

async function updateWithdrawalStatus(id, status, reviewReason = null) {
  const conn = await db.beginTransaction();
  try {
    const [result] = await conn.execute(
      `UPDATE withdrawal_requests
       SET status = ?, review_reason = ?, paid_at = IF(? = 'paid', NOW(), NULL)
       WHERE id = ? AND status = 'pending'`,
      [status, reviewReason, status, id]
    );
    if (result.affectedRows === 0) throw new Error('STATUS_UPDATE_FAILED');
    await db.commit(conn);
    return result;
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = {
  submitWithdrawal,
  createWithdrawal: submitWithdrawal,
  getWithdrawals,
  getWithdrawalsByMerchant: getWithdrawals,
  updateWithdrawalStatus
};

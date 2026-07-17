const db = require('../config/db');

const MAX_RETRIES = 3;

/**
 * 平台管理员查看所有提现申请列表（分页+筛选）
 * @param {number} page — 页码，默认1
 * @param {number} pageSize — 每页条数，默认20
 * @param {string} status — 状态筛选（可选）
 * @param {number} merchantId — 商家ID筛选（可选）
 * @returns {{ list, total, page, pageSize }}
 */
async function getWithdrawals(page = 1, pageSize = 20, status, merchantId) {
  const offset = (page - 1) * pageSize;
  const conditions = [];
  const params = [];

  if (status) {
    conditions.push('status = ?');
    params.push(status);
  }
  if (merchantId) {
    conditions.push('merchant_id = ?');
    params.push(merchantId);
  }

  const whereClause = conditions.length ? ' WHERE ' + conditions.join(' AND ') : '';

  const countSql = `SELECT COUNT(*) as total FROM withdrawal_requests${whereClause}`;
  const dataSql = `SELECT id, request_no, merchant_id, amount, bank_account, status, review_reason, paid_at, created_at, updated_at FROM withdrawal_requests${whereClause} ORDER BY created_at DESC LIMIT ? OFFSET ?`;

  const countRows = await db.query(countSql, params);
  const total = countRows[0] ? countRows[0].total : 0;
  const list = await db.query(dataSql, [...params, pageSize, offset]);

  return { list, total, page, pageSize };
}

/**
 * 平台管理员审批提现申请
 * approve: 状态→paid, 扣减frozen_balance（资金已打款）
 * reject:  状态→rejected, 恢复frozen_balance→balance（资金返还）
 * 使用乐观锁（version）防并发，冲突时重试3次指数退避
 *
 * @param {number} withdrawalId — 提现申请ID
 * @param {'approve'|'reject'} action — 审批动作
 * @param {number} adminId — 管理员用户ID
 * @param {string} reason — 驳回原因（reject时）
 * @returns {{ withdrawalId, status }}
 */
async function approveWithdrawal(withdrawalId, action, adminId, reason) {
  // 1. 查询提现申请，校验状态
  const withdrawals = await db.query(
    'SELECT id, merchant_id, amount, status FROM withdrawal_requests WHERE id = ?',
    [withdrawalId]
  );

  if (!withdrawals.length) throw new Error('WITHDRAWAL_NOT_FOUND');

  const withdrawal = withdrawals[0];

  if (withdrawal.status !== 'pending') throw new Error('ALREADY_PROCESSED');

  const merchantId = withdrawal.merchant_id;
  const amount = parseFloat(withdrawal.amount);

  // 2. 乐观锁重试循环
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    const conn = await db.beginTransaction();
    try {
      // 悲观锁读取当前钱包（防并发：同一商家多笔提现同时审批）
      const [walletRows] = await conn.execute(
        'SELECT balance, frozen_balance, version FROM merchant_wallets WHERE merchant_id = ? FOR UPDATE',
        [merchantId]
      );

      if (!walletRows.length) {
        await db.rollback(conn);
        throw new Error('WALLET_NOT_FOUND');
      }

      const wallet = walletRows[0];
      const currentVersion = wallet.version;
      const currentBalance = parseFloat(wallet.balance);
      const currentFrozen = parseFloat(wallet.frozen_balance);

      if (action === 'approve') {
        // 通过：扣减 frozen_balance（资金已真正打款，从冻结中消除）
        const newFrozenBalance = currentFrozen - amount;
        if (newFrozenBalance < 0) {
          await db.rollback(conn);
          throw new Error('INSUFFICIENT_FROZEN');
        }

        const [updateResult] = await conn.execute(
          'UPDATE merchant_wallets SET frozen_balance = ?, version = version + 1 WHERE merchant_id = ? AND version = ?',
          [newFrozenBalance, merchantId, currentVersion]
        );

        if (updateResult.affectedRows === 0) {
          await db.rollback(conn);
          if (attempt < MAX_RETRIES - 1) {
            await sleep(Math.pow(2, attempt) * 100);
            continue;
          }
          throw new Error('CONFLICT');
        }

        // 更新提现状态→paid
        await conn.execute(
          'UPDATE withdrawal_requests SET status = ?, paid_at = NOW() WHERE id = ?',
          ['paid', withdrawalId]
        );

        // 审计日志
        await conn.execute(
          'INSERT INTO operation_logs (admin_id, action, target_type, target_id, detail) VALUES (?, ?, ?, ?, ?)',
          [adminId, 'approve_withdrawal', 'withdrawal', withdrawalId, JSON.stringify({ action: 'approve', amount, merchant_id: merchantId })]
        );

        await db.commit(conn);
        return { withdrawalId, status: 'paid' };

      } else if (action === 'reject') {
        // 驳回：返还 frozen_balance → balance
        const newBalance = currentBalance + amount;
        const newFrozenBalance = currentFrozen - amount;

        if (newFrozenBalance < 0) {
          await db.rollback(conn);
          throw new Error('INSUFFICIENT_FROZEN');
        }

        const [updateResult] = await conn.execute(
          'UPDATE merchant_wallets SET balance = ?, frozen_balance = ?, version = version + 1 WHERE merchant_id = ? AND version = ?',
          [newBalance, newFrozenBalance, merchantId, currentVersion]
        );

        if (updateResult.affectedRows === 0) {
          await db.rollback(conn);
          if (attempt < MAX_RETRIES - 1) {
            await sleep(Math.pow(2, attempt) * 100);
            continue;
          }
          throw new Error('CONFLICT');
        }

        // 更新提现状态→rejected
        await conn.execute(
          'UPDATE withdrawal_requests SET status = ?, review_reason = ? WHERE id = ?',
          ['rejected', reason, withdrawalId]
        );

        // 审计日志
        await conn.execute(
          'INSERT INTO operation_logs (admin_id, action, target_type, target_id, detail) VALUES (?, ?, ?, ?, ?)',
          [adminId, 'approve_withdrawal', 'withdrawal', withdrawalId, JSON.stringify({ action: 'reject', reason, amount, merchant_id: merchantId })]
        );

        await db.commit(conn);
        return { withdrawalId, status: 'rejected' };
      }

      // 不应到达此处
      await db.rollback(conn);
      throw new Error('INVALID_ACTION');

    } catch (e) {
      await db.rollback(conn);
      // CONFLICT 且未达最大重试次数→继续重试
      if (e.message === 'CONFLICT' && attempt < MAX_RETRIES - 1) continue;
      // 其他错误直接抛出
      throw e;
    }
  }

  // 重试耗尽
  throw new Error('CONFLICT');
}

/**
 * 延迟工具函数
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

module.exports = { getWithdrawals, approveWithdrawal };

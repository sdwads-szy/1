const db = require('../config/db');

/**
 * 管理员查结算列表 — 财务结算管理
 * @param {string|null} status - 状态筛选：pending/confirmed/paid/completed/clawed_back
 * @param {number} page - 页码
 * @param {number} pageSize - 每页条数
 * @returns {{list: Array, total: number, page: number, pageSize: number}}
 */
async function getSettlements(status, page = 1, pageSize = 20) {
  const offset = (page - 1) * pageSize;
  let whereClause = '';
  const params = [];

  if (status) {
    whereClause = 'WHERE so.status = ?';
    params.push(status);
  }

  const countSql = `SELECT COUNT(*) AS total FROM settlement_orders so ${whereClause}`;
  const countResult = await db.query(countSql, params);
  const total = countResult[0].total;

  const dataParams = [...params, pageSize, offset];
  const dataSql = `
    SELECT so.id, so.merchant_id, s.name AS shop_name, so.period, so.amount,
           so.status, so.paid_at, so.created_at
    FROM settlement_orders so
    LEFT JOIN shops s ON so.merchant_id = s.merchant_id
    ${whereClause}
    ORDER BY so.period DESC, so.merchant_id
    LIMIT ? OFFSET ?
  `;
  const rows = await db.query(dataSql, dataParams);

  return {
    list: rows,
    total,
    page,
    pageSize
  };
}

/**
 * 平台结算打款: 校验结算单已确认 → 标记打款 → 钱包入账 → 审计日志
 * 使用事务 + 乐观锁保证数据一致性
 *
 * @param {number} adminId - 管理员用户ID
 * @param {number} settlementId - 结算单ID
 * @returns {{settlementId: number, status: string}}
 * @throws {Error} SETTLEMENT_NOT_FOUND — 结算单不存在
 * @throws {Error} SETTLEMENT_NOT_CONFIRMED — 结算单未确认，无法打款
 * @throws {Error} WALLET_NOT_FOUND — 商家钱包不存在
 * @throws {Error} WALLET_VERSION_CONFLICT — 钱包乐观锁冲突
 */
async function paySettlement(adminId, settlementId) {
  // Step 1: 校验结算单存在且状态为已确认（事务外预检，提供更精确的错误码）
  const settlementRows = await db.query(
    'SELECT * FROM settlement_orders WHERE id = ?',
    [settlementId]
  );
  if (!settlementRows.length) {
    throw new Error('SETTLEMENT_NOT_FOUND');
  }
  const settlement = settlementRows[0];
  if (settlement.status !== 'confirmed') {
    throw new Error('SETTLEMENT_NOT_CONFIRMED');
  }

  // Steps 2-5: 事务包裹 — CAS 状态守卫 + 乐观锁钱包入账 + 审计日志
  const conn = await db.beginTransaction();
  try {
    // Step 2: CAS 状态守卫 — 仅已确认可打款（WHERE status='confirmed' 保证幂等）
    const [updateResult] = await conn.execute(
      'UPDATE settlement_orders SET status = ?, paid_at = NOW() WHERE id = ? AND status = ?',
      ['paid', settlementId, 'confirmed']
    );
    if (updateResult.affectedRows === 0) {
      throw new Error('SETTLEMENT_NOT_CONFIRMED');
    }

    // Step 3: 乐观锁钱包入账 — version 字段防并发
    const [walletRows] = await conn.execute(
      'SELECT id, balance, version FROM merchant_wallets WHERE merchant_id = ?',
      [settlement.merchant_id]
    );
    if (!walletRows || !walletRows.length) {
      throw new Error('WALLET_NOT_FOUND');
    }
    const wallet = walletRows[0];

    const [walletResult] = await conn.execute(
      'UPDATE merchant_wallets SET balance = balance + ?, version = version + 1 WHERE merchant_id = ? AND version = ?',
      [settlement.amount, settlement.merchant_id, wallet.version]
    );
    if (walletResult.affectedRows === 0) {
      throw new Error('WALLET_VERSION_CONFLICT');
    }

    // Step 4: 运营审计日志
    await conn.execute(
      'INSERT INTO operation_logs (admin_id, action, target_type, target_id, detail) VALUES (?, ?, ?, ?, ?)',
      [
        adminId,
        'settlement_pay',
        'settlement',
        settlementId,
        JSON.stringify({
          before: 'confirmed',
          after: 'paid',
          amount: settlement.amount,
          merchant_id: settlement.merchant_id,
          period: settlement.period
        })
      ]
    );

    // Step 5: 提交事务
    await db.commit(conn);

    return { settlementId, status: 'paid' };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = { getSettlements: getSettlements, paySettlement: paySettlement };

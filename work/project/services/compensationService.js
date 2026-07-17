const db = require('../config/db');
const logger = require('../config/logger');

/**
 * 补偿服务 — 处理超时取消、支付回调恢复、库存释放、余额扣减等异常补偿逻辑
 * 覆盖场景树 §2.5 全部 4 条补偿路径
 */

// ── 工具函数 ──────────────────────────────────────────────

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 通用重试操作（指数退避）
 * @param {Function} fn - 异步操作函数
 * @param {number} maxRetries - 最大重试次数 默认 3
 * @param {number} baseBackoffMs - 基础退避时间(ms) 默认 100
 * @returns {Promise<any>}
 */
async function retryOperation(fn, maxRetries = 3, baseBackoffMs = 100) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === maxRetries - 1) throw e;
      const backoff = baseBackoffMs * Math.pow(2, i);
      logger.warn(`[COMPENSATION] 重试 ${i + 1}/${maxRetries}，${backoff}ms 后重试`, { error: e.message });
      await sleep(backoff);
    }
  }
}

// ── 2.5.1 支付超时取消 ────────────────────────────────────

/**
 * 取消单笔超时未支付订单
 * 触发: BullMQ 延迟任务 (order.created_at + 30min)
 * 步骤:
 *   1. 幂等检查: 非 pending 状态直接终止
 *   2. 事务: UPDATE orders→cancelled + UPDATE sub_orders→cancelled + 释放库存
 *   3. affectedRows==0 → ROLLBACK → 重试 3 次(间隔 5s)
 * @param {string} orderNo - 主订单号
 * @returns {Promise<{cancelled: boolean, reason?: string}>}
 */
async function cancelTimeoutOrder(orderNo) {
  // 1. 幂等检查
  const orders = await db.query(
    'SELECT id, order_no, status FROM orders WHERE order_no = ?',
    [orderNo]
  );

  if (!orders.length) {
    logger.warn(`[COMPENSATION] 订单不存在: ${orderNo}`);
    return { cancelled: false, reason: 'ORDER_NOT_FOUND' };
  }

  const order = orders[0];

  if (order.status !== 'pending') {
    logger.info(`[COMPENSATION] 订单 ${orderNo} 当前状态 ${order.status}，跳过取消`);
    return { cancelled: false, reason: 'ALREADY_PROCESSED' };
  }

  // 2. 事务: 取消订单 + 释放库存（带重试）
  return retryOperation(async () => {
    const conn = await db.beginTransaction();
    try {
      // 2a. 更新主订单状态
      const [orderResult] = await conn.execute(
        "UPDATE orders SET status = 'cancelled' WHERE order_no = ? AND status = 'pending'",
        [orderNo]
      );

      if (orderResult.affectedRows === 0) {
        await db.rollback(conn);
        throw new Error('CONCURRENT_MODIFICATION');
      }

      // 2b. 查询关联子订单
      const [subOrders] = await conn.execute(
        'SELECT id, sub_order_no, shop_id FROM sub_orders WHERE order_id = ?',
        [order.id]
      );

      // 2c. 批量取消子订单
      if (subOrders.length > 0) {
        const subOrderIds = subOrders.map(so => so.id);
        const placeholders = subOrderIds.map(() => '?').join(',');
        await conn.execute(
          `UPDATE sub_orders SET status = 'cancelled' WHERE id IN (${placeholders}) AND status = 'pending'`,
          subOrderIds
        );
      }

      // 2d. 释放库存: 遍历 order_items 恢复 stock + 减少 frozen_stock
      for (const subOrder of subOrders) {
        const [items] = await conn.execute(
          'SELECT sku_id, quantity FROM order_items WHERE sub_order_id = ?',
          [subOrder.id]
        );

        for (const item of items) {
          const [invResult] = await conn.execute(
            'UPDATE inventories SET stock = stock + ?, frozen_stock = GREATEST(frozen_stock - ?, 0), version = version + 1 WHERE sku_id = ? AND shop_id = ?',
            [item.quantity, item.quantity, item.sku_id, subOrder.shop_id]
          );

          if (invResult.affectedRows === 0) {
            logger.error(
              `[COMPENSATION] 库存记录缺失 sku_id=${item.sku_id} shop_id=${subOrder.shop_id}`
            );
          }
        }
      }

      await db.commit(conn);
      logger.info(`[COMPENSATION] 订单 ${orderNo} 超时取消成功`);
      return { cancelled: true };

    } catch (e) {
      await db.rollback(conn);
      throw e;
    }
  }, 3, 5000); // 3 次重试, 间隔 5s
}

/**
 * 批量扫描并取消所有超时未支付订单
 * 定时任务入口: 建议每 2 分钟执行一次
 * @param {number} timeoutMinutes - 超时分钟数 默认 30
 * @returns {Promise<{processed: number, cancelled: number, failed: number}>}
 */
async function cancelAllTimeoutOrders(timeoutMinutes = 30) {
  let processed = 0;
  let cancelled = 0;
  let failed = 0;

  try {
    const expiredOrders = await db.query(
      "SELECT order_no FROM orders WHERE status = 'pending' AND created_at < DATE_SUB(NOW(), INTERVAL ? MINUTE) LIMIT 100",
      [timeoutMinutes]
    );

    logger.info(`[COMPENSATION] 扫描到 ${expiredOrders.length} 笔超时待取消订单`);

    for (const row of expiredOrders) {
      processed++;
      try {
        const result = await cancelTimeoutOrder(row.order_no);
        if (result.cancelled) cancelled++;
      } catch (e) {
        failed++;
        logger.error(`[COMPENSATION] 取消订单 ${row.order_no} 失败`, { error: e.message });
      }
    }

    return { processed, cancelled, failed };
  } catch (e) {
    logger.error('[COMPENSATION] 批量取消超时订单失败', { error: e.message });
    throw e;
  }
}

// ── 2.5.2 支付回调丢失恢复 ────────────────────────────────

/**
 * 恢复丢失的支付回调
 * 触发: 定时任务（每 5 分钟）
 * 步骤:
 *   1. SELECT payments WHERE status='pending' AND created_at < NOW()-5min
 *   2. mock 模式 → 直接标记 success + 更新子订单/主订单
 *   3. real 模式 → 调用支付网关查询（占位）
 *   4. 最多查询 12 次(1小时), 仍无结果 → 标记人工对账
 * @returns {Promise<{recovered: number, failed: number, needsManual: number}>}
 */
async function recoverLostPayments() {
  const PAYMENT_MODE = process.env.PAYMENT_MODE || 'mock';
  let recovered = 0;
  let failed = 0;
  let needsManual = 0;
  try {
    const stalePayments = await db.query(
      "SELECT id, transaction_no, sub_order_id, order_id, channel FROM payments WHERE status = 'pending' AND created_at < DATE_SUB(NOW(), INTERVAL 5 MINUTE)"
    );

    if (stalePayments.length === 0) {
      return { recovered: 0, failed: 0, needsManual: 0 };
    }

    logger.info(`[COMPENSATION] 发现 ${stalePayments.length} 笔待恢复支付记录`);

    for (const payment of stalePayments) {
      try {
        if (PAYMENT_MODE === 'mock') {
          await _mockRecoverPayment(payment);
          recovered++;
        } else {
          const realResult = await _realRecoverPayment(payment);
          if (realResult === 'recovered') recovered++;
          else if (realResult === 'needs_manual') needsManual++;
          else failed++;
        }
      } catch (e) {
        failed++;
        logger.error(`[COMPENSATION] 恢复支付 ${payment.transaction_no} 失败`, { error: e.message });
      }
    }

    logger.info(
      `[COMPENSATION] 支付恢复完成: ${recovered} 已恢复, ${failed} 失败, ${needsManual} 需人工`
    );
    return { recovered, failed, needsManual };

  } catch (e) {
    logger.error('[COMPENSATION] 支付回调恢复批处理失败', { error: e.message });
    throw e;
  }

}
/**
 * Mock 模式: 直接标记支付成功并更新订单状态
 * @param {Object} payment - 支付记录
 * @returns {Promise<void>}
 */
async function _mockRecoverPayment(payment) {
  const conn = await db.beginTransaction();
  try {
    // 更新支付记录
    await conn.execute(
      "UPDATE payments SET status = 'success', callback_log = ? WHERE id = ? AND status = 'pending'",
      [JSON.stringify({ mock: true, recovered: true, recovered_at: new Date().toISOString() }), payment.id]
    );

    // 更新子订单状态
    await conn.execute(
      "UPDATE sub_orders SET status = 'paid' WHERE id = ? AND status = 'pending'",
      [payment.sub_order_id]
    );

    // 检查主订单下是否所有子订单都已支付
    const [pendingSubRows] = await conn.execute(
      "SELECT COUNT(*) as cnt FROM sub_orders WHERE order_id = ? AND status = 'pending'",
      [payment.order_id]
    );

    if (pendingSubRows[0].cnt === 0) {
      await conn.execute(
        "UPDATE orders SET status = 'paid', paid_at = NOW() WHERE id = ? AND status = 'pending'",
        [payment.order_id]
      );
    }

    await db.commit(conn);
    logger.info(`[COMPENSATION] Mock 恢复支付 ${payment.transaction_no}`);
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * Real 模式: 调用支付网关主动查单
 * @param {Object} payment - 支付记录
 * @returns {Promise<'recovered'|'needs_manual'|'failed'>}
 */
async function _realRecoverPayment(payment) {
  // 查询该支付记录已被恢复的次数
  const countRows = await db.query(
    "SELECT JSON_LENGTH(COALESCE(callback_log->'$.recovery_attempts', '[]')) as attempts FROM payments WHERE id = ?",
    [payment.id]
  );
  const attempts = countRows[0]?.attempts || 0;

  // 超过 12 次 → 标记人工对账
  if (attempts >= 12) {
    await db.query(
      "UPDATE payments SET callback_log = JSON_SET(COALESCE(callback_log, '{}'), '$.needs_manual_review', true, '$.manual_review_reason', '超过12次自动恢复失败') WHERE id = ?",
      [payment.id]
    );
    logger.warn(`[COMPENSATION] 支付 ${payment.transaction_no} 超过12次恢复失败，需人工对账`);
    return 'needs_manual';
  }

  // Real: 调用支付网关 SDK 查询订单状态（占位 — 集成时替换）
  // const gatewayResult = await paymentGateway.query({ transactionNo: payment.transaction_no });
  // if (gatewayResult.status === 'SUCCESS') { ... }

  // 当前无真实网关，记录查询尝试
  await db.query(
    "UPDATE payments SET callback_log = JSON_ARRAY_APPEND(COALESCE(callback_log, '{}'), '$.recovery_attempts', ?) WHERE id = ?",
    [JSON.stringify({ attempted_at: new Date().toISOString(), channel: payment.channel }), payment.id]
  );

  logger.info(`[COMPENSATION] Real 模式: 查询支付网关 ${payment.transaction_no} (第 ${attempts + 1} 次)`);
  return 'failed';
}

// ── 2.5.3 库存乐观锁扣减重试 ──────────────────────────────

/**
 * 库存扣减（乐观锁 + 重试）
 * 触发: 下单时 version 冲突
 * 步骤:
 *   1. UPDATE inventories SET stock=stock-?, version=version+1 WHERE sku_id=? AND shop_id=? AND version=? AND stock>=?
 *   2. affectedRows==0 → 重试（最多 3 次，指数退避 100/200/400ms）
 *   3. 3 次均失败 → throw INSUFFICIENT_STOCK
 * @param {number} skuId - SKU ID
 * @param {number} shopId - 店铺 ID
 * @param {number} quantity - 扣减数量
 * @returns {Promise<{success: boolean, newVersion?: number}>}
 */
async function deductInventoryWithRetry(skuId, shopId, quantity) {
  return retryOperation(async () => {
    // 先查询当前版本号
    const rows = await db.query(
      'SELECT stock, version FROM inventories WHERE sku_id = ? AND shop_id = ?',
      [skuId, shopId]
    );

    if (!rows.length) {
      throw new Error('INVENTORY_NOT_FOUND');
    }

    const inv = rows[0];

    if (inv.stock < quantity) {
      throw new Error('INSUFFICIENT_STOCK');
    }

    // 乐观锁更新
    const result = await db.query(
      'UPDATE inventories SET stock = stock - ?, frozen_stock = frozen_stock + ?, version = version + 1 WHERE sku_id = ? AND shop_id = ? AND version = ? AND stock >= ?',
      [quantity, quantity, skuId, shopId, inv.version, quantity]
    );

    if (result.affectedRows === 0) {
      throw new Error('VERSION_CONFLICT');
    }

    return { success: true, newVersion: inv.version + 1 };
  }, 3, 100);
}

/**
 * 释放订单占用的库存（下单失败回滚时调用）
 * @param {number} orderId - 主订单 ID
 * @returns {Promise<void>}
 */
async function releaseInventoryForOrder(orderId) {
  const conn = await db.beginTransaction();
  try {
    const [subOrders] = await conn.execute(
      'SELECT id, shop_id FROM sub_orders WHERE order_id = ?',
      [orderId]
    );

    for (const subOrder of subOrders) {
      const [items] = await conn.execute(
        'SELECT sku_id, quantity FROM order_items WHERE sub_order_id = ?',
        [subOrder.id]
      );

      for (const item of items) {
        await conn.execute(
          'UPDATE inventories SET stock = stock + ?, frozen_stock = GREATEST(frozen_stock - ?, 0), version = version + 1 WHERE sku_id = ? AND shop_id = ?',
          [item.quantity, item.quantity, item.sku_id, subOrder.shop_id]
        );
      }
    }

    await db.commit(conn);
    logger.info(`[COMPENSATION] 订单 ${orderId} 库存已释放`);
  } catch (e) {
    await db.rollback(conn);
    logger.error(`[COMPENSATION] 释放订单 ${orderId} 库存失败`, { error: e.message });
    throw e;
  }
}

// ── 2.5.4 钱包余额扣减（乐观锁）────────────────────────────

/**
 * 商家钱包余额扣减（乐观锁 + 事务）
 * 触发: 提现申请 / 退款追索
 * 步骤:
 *   1. BEGIN TX: SELECT balance, version FROM merchant_wallets WHERE merchant_id=?
 *   2. balance < amount → ROLLBACK, throw INSUFFICIENT_BALANCE
 *   3. UPDATE merchant_wallets SET balance=balance-?, version=version+1 WHERE version=?
 *   4. version 冲突 → throw VERSION_CONFLICT（调用方提示"余额已变动,请刷新重试"）
 * @param {number} merchantId - 商家 ID
 * @param {number} amount - 扣减金额
 * @returns {Promise<{success: boolean, newBalance: number}>}
 */
async function deductWalletBalance(merchantId, amount) {
  const conn = await db.beginTransaction();
  try {
    const [rows] = await conn.execute(
      'SELECT balance, version FROM merchant_wallets WHERE merchant_id = ?',
      [merchantId]
    );

    if (!rows.length) {
      await db.rollback(conn);
      throw new Error('WALLET_NOT_FOUND');
    }

    const wallet = rows[0];
    const balance = parseFloat(wallet.balance);

    if (balance < amount) {
      await db.rollback(conn);
      throw new Error('INSUFFICIENT_BALANCE');
    }

    const [result] = await conn.execute(
      'UPDATE merchant_wallets SET balance = balance - ?, version = version + 1 WHERE merchant_id = ? AND version = ? AND balance >= ?',
      [amount, merchantId, wallet.version, amount]
    );

    if (result.affectedRows === 0) {
      await db.rollback(conn);
      throw new Error('VERSION_CONFLICT');
    }

    await db.commit(conn);
    return { success: true, newBalance: balance - amount };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 商家钱包余额增加（用于退款/结算等入账场景）
 * @param {number} merchantId - 商家 ID
 * @param {number} amount - 增加金额
 * @returns {Promise<{success: boolean, newBalance: number}>}
 */
async function creditWalletBalance(merchantId, amount) {
  const conn = await db.beginTransaction();
  try {
    const [rows] = await conn.execute(
      'SELECT balance, version FROM merchant_wallets WHERE merchant_id = ?',
      [merchantId]
    );

    if (!rows.length) {
      await db.rollback(conn);
      throw new Error('WALLET_NOT_FOUND');
    }

    const wallet = rows[0];

    const [result] = await conn.execute(
      'UPDATE merchant_wallets SET balance = balance + ?, total_earned = total_earned + ?, version = version + 1 WHERE merchant_id = ? AND version = ?',
      [amount, amount, merchantId, wallet.version]
    );

    if (result.affectedRows === 0) {
      await db.rollback(conn);
      throw new Error('VERSION_CONFLICT');
    }

    await db.commit(conn);
    return { success: true, newBalance: parseFloat(wallet.balance) + amount };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = {
  cancelTimeoutOrder,
  cancelAllTimeoutOrders,
  recoverLostPayments,
  deductInventoryWithRetry,
  releaseInventoryForOrder,
  deductWalletBalance,
  creditWalletBalance,
  retryOperation
};

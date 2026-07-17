const db = require('../config/db');
const crypto = require('crypto');

const PAYMENT_MODE = process.env.PAYMENT_MODE || 'mock';

/**
 * 生成唯一交易流水号
 */
function generateTransactionNo() {
  const timestamp = Date.now().toString(36).toUpperCase();
  const random = crypto.randomBytes(6).toString('hex').toUpperCase();
  return `TXN${timestamp}${random}`;
}

/**
 * 发起支付
 * @param {number} userId - 当前用户ID（来自 token）
 * @param {string} orderNo - 主订单号
 * @param {string} channel - 支付渠道 (wechat/alipay/unionpay)
 * @returns {{ paymentUrl: string, transactionNos: string[], totalAmount: string }}
 */
async function pay(userId, orderNo, channel) {
  // 1. 查询主订单
  const orders = await db.query(
    'SELECT id, user_id, total_amount, status, created_at FROM orders WHERE order_no = ?',
    [orderNo]
  );
  if (!orders.length) throw new Error('ORDER_NOT_FOUND');
  const order = orders[0];

  // 2. 校验订单归属
  if (order.user_id !== userId) throw new Error('FORBIDDEN');

  // 3. 校验订单状态（只有待付款才能支付）
  if (order.status !== 'pending') throw new Error('ORDER_STATUS_INVALID');

  // 4. 校验订单未超时（30分钟）
  const created = new Date(order.created_at).getTime();
  const now = Date.now();
  if (now - created > 30 * 60 * 1000) throw new Error('ORDER_TIMEOUT');

  // 5. 查询子订单
  const subOrders = await db.query(
    'SELECT id, sub_order_no, amount, status FROM sub_orders WHERE order_id = ?',
    [order.id]
  );

  if (!subOrders.length) {
    throw new Error('ORDER_NOT_FOUND');
  }

  // 6. 检查是否已有支付记录（幂等）
  const existingPayments = await db.query(
    'SELECT p.id, p.status FROM payments p JOIN sub_orders so ON p.sub_order_id = so.id WHERE so.order_id = ?',
    [order.id]
  );

  if (existingPayments.length > 0) {
    const anyPending = existingPayments.some(function(p) { return p.status === 'pending'; });
    if (anyPending) throw new Error('DUPLICATE_PAYMENT');
    // 已有成功/失败记录，返回已存在的结果
    const allSuccess = existingPayments.every(function(p) { return p.status === 'success'; });
    return {
      paymentUrl: '/checkout/pay?orderNo=' + orderNo,
      transactionNos: [],
      totalAmount: order.total_amount,
      alreadyPaid: allSuccess,
      mockHint: PAYMENT_MODE === 'mock' ? '模拟支付环境，支付将自动完成' : undefined
    };
  }

  // 7. 创建支付记录（事务）
  const conn = await db.beginTransaction();
  try {
    const paymentResults = [];
    for (var i = 0; i < subOrders.length; i++) {
      var so = subOrders[i];
      var txnNo = generateTransactionNo();
      await conn.execute(
        'INSERT INTO payments (transaction_no, sub_order_id, channel, amount, status) VALUES (?, ?, ?, ?, ?)',
        [txnNo, so.id, channel, so.amount, 'pending']
      );
      paymentResults.push({ transaction_no: txnNo, sub_order_id: so.id, amount: so.amount });
    }
    await db.commit(conn);

    // 8. 返回支付信息
    var result = {
      paymentUrl: '/checkout/pay?orderNo=' + orderNo,
      transactionNos: paymentResults.map(function(p) { return p.transaction_no; }),
      totalAmount: order.total_amount
    };

    if (PAYMENT_MODE === 'mock') {
      result.mockHint = '模拟支付环境，支付将自动完成';
    }

    return result;
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 查询支付状态（轮询）
 * mock 模式下首次轮询自动完成支付
 * @param {number} userId - 当前用户ID
 * @param {string} orderNo - 主订单号
 * @returns {{ status: string, orderNo: string }}
 */
async function getPaymentStatus(userId, orderNo) {
  // 1. 查询主订单
  const orders = await db.query(
    'SELECT id, user_id, status FROM orders WHERE order_no = ?',
    [orderNo]
  );
  if (!orders.length) throw new Error('ORDER_NOT_FOUND');
  const order = orders[0];

  // 2. 校验归属
  if (order.user_id !== userId) throw new Error('FORBIDDEN');

  // 3. 终态直接返回
  if (order.status === 'paid' || order.status === 'shipped' || order.status === 'completed') {
    return { status: 'success', orderNo: orderNo };
  }
  if (order.status === 'cancelled') {
    return { status: 'failed', orderNo: orderNo, reason: '订单已取消' };
  }
  if (order.status === 'refunding' || order.status === 'refunded') {
    return { status: 'success', orderNo: orderNo };
  }

  // 4. 查询子订单的支付记录
  const payments = await db.query(
    'SELECT p.id, p.transaction_no, p.status FROM payments p JOIN sub_orders so ON p.sub_order_id = so.id WHERE so.order_id = ?',
    [order.id]
  );
  if (!payments.length) {
    return { status: 'pending', orderNo: orderNo };
  }

  // 5. mock 模式：自动完成支付
  if (PAYMENT_MODE === 'mock') {
    const conn = await db.beginTransaction();
    try {
      // 更新支付记录为成功
      for (var i = 0; i < payments.length; i++) {
        var p = payments[i];
        if (p.status === 'pending') {
          await conn.execute(
            'UPDATE payments SET status = ? WHERE id = ? AND status = ?',
            ['success', p.id, 'pending']
          );
        }
      }

      // 更新子订单状态
      await conn.execute(
        'UPDATE sub_orders SET status = ? WHERE order_id = ? AND status = ?',
        ['paid', order.id, 'pending']
      );

      // 更新主订单状态
      var result = await conn.execute(
        'UPDATE orders SET status = ?, paid_at = NOW() WHERE id = ? AND status = ?',
        ['paid', order.id, 'pending']
      );

      await db.commit(conn);

      return {
        status: 'success',
        orderNo: orderNo,
        mockHint: result.affectedRows > 0 ? '模拟支付已自动完成' : '支付已完成'
      };
    } catch (e) {
      await db.rollback(conn);
      throw e;
    }
  }

  // 6. real 模式：检查支付状态
  var allSuccess = payments.every(function(p) { return p.status === 'success'; });
  var anyFailed = payments.some(function(p) { return p.status === 'failed'; });

  if (allSuccess) {
    // 所有支付成功，同步更新订单状态
    const conn = await db.beginTransaction();
    try {
      await conn.execute(
        'UPDATE sub_orders SET status = ? WHERE order_id = ? AND status = ?',
        ['paid', order.id, 'pending']
      );
      await conn.execute(
        'UPDATE orders SET status = ?, paid_at = NOW() WHERE id = ? AND status = ?',
        ['paid', order.id, 'pending']
      );
      await db.commit(conn);
    } catch (e) {
      await db.rollback(conn);
      // 订单状态同步失败不影响支付状态返回
    }
    return { status: 'success', orderNo: orderNo };
  }

  if (anyFailed) {
    return { status: 'failed', orderNo: orderNo, reason: '支付失败' };
  }

  return { status: 'pending', orderNo: orderNo };
}

module.exports = { pay: pay, getPaymentStatus: getPaymentStatus };

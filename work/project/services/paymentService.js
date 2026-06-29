const db = require('../config/db');
const crypto = require('crypto');

// ============ 支付网关模拟 ============
// 生产环境替换为真实支付网关 SDK（微信支付/支付宝）

/**
 * 调用第三方支付网关生成预支付订单
 * 模拟实现：生成支付链接和二维码标识
 */
async function callPaymentGateway(orderNo, amount, channel) {
  const tradeNo = `SIM${Date.now()}${Math.random().toString(36).substring(2, 10).toUpperCase()}`;
  const payUrl =
    channel === 'wxpay'
      ? `https://pay.example.com/wxpay/order/${orderNo}`
      : `https://pay.example.com/alipay/order/${orderNo}`;

  return {
    success: true,
    tradeNo,
    payUrl,
    qrCode: `qr://${channel}/${orderNo}/${tradeNo}`
  };
}

// ============ DB-API: CRUD ============

/**
 * 创建支付记录
 * @param {Object} data — { order_id, user_id, amount, channel }
 * @returns {{ insertId: number }}
 */
async function createPayment(data) {
  const result = await db.query(
    'INSERT INTO payments (order_id, user_id, amount, channel) VALUES (?, ?, ?, ?)',
    [data.order_id, data.user_id, data.amount, data.channel]
  );
  return { insertId: result.insertId };
}

/**
 * 按 ID 查询支付记录
 * @param {number} id
 * @returns {Object} payment 行
 */
async function findPaymentById(id) {
  const rows = await db.query('SELECT * FROM payments WHERE id = ?', [id]);
  if (!rows.length) throw new Error('NOT_FOUND');
  return rows[0];
}

/**
 * 按订单 ID 查询最新支付记录
 * @param {number} orderId
 * @returns {Object} payment 行
 */
async function findPaymentByOrderId(orderId) {
  const rows = await db.query(
    'SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1',
    [orderId]
  );
  if (!rows.length) throw new Error('NOT_FOUND');
  return rows[0];
}

/**
 * 更新支付记录状态
 * @param {number} id
 * @param {Object} data — { status?, trade_no?, paid_at?, refund_amount? }
 * @returns {{ affectedRows: number }}
 */
async function updatePaymentStatus(id, data) {
  const fields = [];
  const params = [];

  if (data.status !== undefined) {
    fields.push('status = ?');
    params.push(data.status);
  }
  if (data.trade_no !== undefined) {
    fields.push('trade_no = ?');
    params.push(data.trade_no);
  }
  if (data.paid_at !== undefined) {
    fields.push('paid_at = ?');
    params.push(data.paid_at);
  }
  if (data.refund_amount !== undefined) {
    fields.push('refund_amount = ?');
    params.push(data.refund_amount);
  }

  if (!fields.length) return { affectedRows: 0 };

  params.push(id);
  const result = await db.query(
    `UPDATE payments SET ${fields.join(', ')} WHERE id = ?`,
    params
  );
  return { affectedRows: result.affectedRows };
}

// ============ 业务逻辑 ============

/**
 * 发起支付
 * 幂等：同一笔 payment 重复调用不重复生成支付链接
 */
async function pay(paymentId, channel, userId) {
  // 1. 查询支付记录
  const payment = await findPaymentById(paymentId);

  // 2. 归属校验
  if (payment.user_id !== userId) {
    throw new Error('FORBIDDEN');
  }

  // 3. 幂等：已支付直接拒绝
  if (payment.status === 'paid') {
    throw new Error('ORDER_ALREADY_PAID');
  }

  // 4. 已关闭 / 退款中 / 已退款 — 不可再支付
  if (payment.status !== 'pending') {
    throw new Error('INVALID_STATUS');
  }

  // 5. 校验关联订单状态
  const orderRows = await db.query('SELECT * FROM orders WHERE id = ?', [payment.order_id]);
  if (!orderRows.length) throw new Error('NOT_FOUND');
  const order = orderRows[0];

  const nonPayableStatuses = ['paid', 'shipped', 'received', 'completed', 'refunding'];
  if (nonPayableStatuses.includes(order.status)) {
    throw new Error('ORDER_ALREADY_PAID');
  }
  if (order.status === 'cancelled') {
    throw new Error('PAYMENT_TIMEOUT');
  }

  // 6. 调用支付网关（指数退避重试，最多 3 次）
  let gatewayResult;
  const maxRetries = 3;
  for (let i = 0; i < maxRetries; i++) {
    try {
      gatewayResult = await callPaymentGateway(order.order_no, payment.amount, channel);
      break;
    } catch (e) {
      if (i === maxRetries - 1) throw new Error('GATEWAY_ERROR');
      await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
    }
  }

  // 7. 若渠道变更则同步更新
  if (payment.channel !== channel) {
    await db.query('UPDATE payments SET channel = ? WHERE id = ?', [channel, paymentId]);
  }

  return {
    payUrl: gatewayResult.payUrl,
    qrCode: gatewayResult.qrCode
  };
}

/**
 * 处理支付网关回调
 * 签名验证 → 查订单 → 查支付 → 原子更新支付+订单状态
 */
async function handleCallback(data) {
  const { tradeNo, orderNo, status, sign } = data;

  // 1. 验证签名
  if (!verifySign({ tradeNo, orderNo, status }, sign)) {
    throw new Error('INVALID_SIGN');
  }

  // 2. 按订单号查订单
  const orderRows = await db.query('SELECT * FROM orders WHERE order_no = ?', [orderNo]);
  if (!orderRows.length) throw new Error('NOT_FOUND');
  const order = orderRows[0];

  // 3. 按订单 ID 查支付记录
  const payment = await findPaymentByOrderId(order.id);

  // 4. 幂等：已处理直接返回成功
  if (payment.status === 'paid') {
    return { code: 'SUCCESS', message: 'Already processed' };
  }

  // 5. 非 pending 状态不处理（已关闭/退款中/已退款）
  if (payment.status !== 'pending') {
    return { code: 'FAIL', message: 'Payment not in payable state' };
  }

  // 6. 网关通知支付失败 → 关闭支付记录
  if (status !== 'SUCCESS') {
    await db.query('UPDATE payments SET status = ? WHERE id = ? AND status = ?', [
      'closed',
      payment.id,
      'pending'
    ]);
    return { code: 'FAIL', message: 'Payment failed at gateway' };
  }

  // 7. 支付成功：事务内原子更新 payments + orders
  const conn = await db.beginTransaction();
  try {
    // 更新支付记录
    const payUpdate = await conn.execute(
      'UPDATE payments SET status = ?, trade_no = ?, paid_at = NOW() WHERE id = ? AND status = ?',
      ['paid', tradeNo, payment.id, 'pending']
    );

    if (!payUpdate.affectedRows) {
      await db.rollback(conn);
      return { code: 'FAIL', message: 'Concurrent update conflict' };
    }

    // 更新订单状态
    const orderUpdate = await conn.execute(
      'UPDATE orders SET status = ?, pay_time = NOW(), pay_method = ? WHERE id = ? AND status = ?',
      ['paid', payment.channel, order.id, 'pending_pay']
    );

    if (!orderUpdate.affectedRows) {
      await db.rollback(conn);
      return { code: 'FAIL', message: 'Order status conflict' };
    }

    await db.commit(conn);
    return { code: 'SUCCESS' };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 查询支付状态
 */
async function getPaymentStatus(paymentId, userId) {
  const payment = await findPaymentById(paymentId);

  if (payment.user_id !== userId) {
    throw new Error('FORBIDDEN');
  }

  return {
    status: payment.status,
    paidAt: payment.paid_at,
    tradeNo: payment.trade_no,
    channel: payment.channel,
    amount: String(payment.amount)
  };
}

// ============ 签名工具 ============

/**
 * 生成回调签名（MD5）
 */
function generateSign(data) {
  const secret = process.env.PAYMENT_GATEWAY_SECRET || 'default-payment-secret';
  const signStr = `${data.tradeNo}|${data.orderNo}|${data.status}|${secret}`;
  return crypto.createHash('md5').update(signStr).digest('hex').toUpperCase();
}

/**
 * 验证回调签名
 */
function verifySign(data, receivedSign) {
  const expectedSign = generateSign(data);
  return expectedSign === receivedSign;
}

module.exports = {
  createPayment,
  findPaymentById,
  findPaymentByOrderId,
  updatePaymentStatus,
  pay,
  handleCallback,
  getPaymentStatus
};

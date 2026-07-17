const db = require('../config/db');

const SMS_MODE = process.env.SMS_MODE || 'mock';
const MOCK_CODE = '123456';

/**
 * 验证短信验证码
 * mock模式：固定验证码 123456
 * real模式：校验Redis中的验证码（5分钟有效期）
 */
async function verifySmsCode(mobile, code) {
  if (SMS_MODE === 'mock') {
    if (code === MOCK_CODE) {
      return true;
    }
    throw new Error('INVALID_CODE');
  }

  // real模式：从Redis读取并校验
  // real模式：从Redis读取并校验
  const redis = require('../config/redis');
  const storedCode = await redis.get(`sms:${mobile}`);
  if (!storedCode) {
    throw new Error('CODE_EXPIRED');
  }
  if (storedCode !== code) {
    throw new Error('INVALID_CODE');
  }
  // 校验通过后删除已使用的验证码
  await redis.del(`sms:${mobile}`);
  return true;
}

/**
 * 商家入驻申请
 * 验证码校验 → 唯一性检查 → 创建merchant+shop+wallet → 更新用户角色
 */
async function registerMerchant(userId, mobile, code, creditCode, bizLicense, shopName, logo) {
  // Step 1: 短信验证码校验
  await verifySmsCode(mobile, code);

  // Step 2: 检查统一社会信用代码唯一性
  const existingMerchant = await db.query(
    'SELECT id FROM merchants WHERE credit_code = ? OR user_id = ?',
    [creditCode, userId]
  );
  if (existingMerchant.length > 0) {
    if (existingMerchant[0].credit_code === creditCode || existingMerchant.some(m => m.credit_code === creditCode)) {
      // 检查具体是哪条匹配了 credit_code
      const byCode = await db.query('SELECT id FROM merchants WHERE credit_code = ?', [creditCode]);
      if (byCode.length > 0) {
        throw new Error('DUPLICATE_CREDIT_CODE');
      }
    }
    throw new Error('DUPLICATE_CREDIT_CODE');
  }

  // Step 3: 检查店铺名称唯一性
  const existingShop = await db.query('SELECT id FROM shops WHERE name = ?', [shopName]);
  if (existingShop.length > 0) {
    throw new Error('DUPLICATE_SHOP_NAME');
  }

  // Step 4-7: 事务 — 创建商家 + 店铺 + 更新用户角色 + 初始化钱包
  const conn = await db.beginTransaction();
  try {
    // Step 4: INSERT merchants
    const [merchantResult] = await conn.execute(
      'INSERT INTO merchants (user_id, credit_code, biz_license, contact_name, contact_mobile, status) VALUES (?, ?, ?, ?, ?, ?)',
      [userId, creditCode, bizLicense, mobile, mobile, 'pending_review']
    );
    const merchantId = merchantResult.insertId;

    // INSERT shops
    const [shopResult] = await conn.execute(
      'INSERT INTO shops (merchant_id, name, logo, status) VALUES (?, ?, ?, ?)',
      [merchantId, shopName, logo || null, 'open']
    );

    // Step 5: UPDATE users role
    await conn.execute('UPDATE users SET role = ? WHERE id = ?', ['merchant', userId]);

    // Step 6: INSERT merchant_wallets (初始余额0)
    await conn.execute(
      'INSERT INTO merchant_wallets (merchant_id, balance, frozen_balance, total_earned, version) VALUES (?, 0.00, 0.00, 0.00, 0)',
      [merchantId]
    );

    // Step 7: COMMIT
    await db.commit(conn);

    return {
      applicationId: merchantId,
      status: 'pending_review',
    };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 查询入驻审核状态
 * 根据 userId 查询关联的商家申请记录
 */
async function getRegisterStatus(userId) {
  const rows = await db.query(
    'SELECT id, status, review_reason, reviewed_at, created_at FROM merchants WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
    [userId]
  );

  if (rows.length === 0) {
    throw new Error('NO_APPLICATION');
  }

  const row = rows[0];
  return {
    applicationId: row.id,
    status: row.status,
    reviewReason: row.review_reason || null,
    reviewedAt: row.reviewed_at ? row.reviewed_at.toISOString() : null,
  };
}

module.exports = { registerMerchant, getRegisterStatus };

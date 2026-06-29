const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const db = require('../config/db');
const redis = require('../config/redis');
const { encrypt } = require('../utils/encryption');
const logger = require('../config/logger');

const SALT_ROUNDS = 10;
const JWT_SECRET = process.env.JWT_SECRET;
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';

// ==================== 商家注册 ====================

/**
 * 商家注册：验证码校验 → 创建用户(merchant角色) → 创建店铺(pending) → 签发JWT
 * @param {string} phone
 * @param {string} verifyCode
 * @param {string} password
 * @returns {{ userId: number, shopId: number, token: string }}
 */
async function registerMerchant(phone, verifyCode, password) {
  // 格式校验
  if (!phone || !/^1[3-9]\d{9}$/.test(phone)) {
    throw new Error('INVALID_PHONE');
  }

  // 验证码校验（Redis）
  const storedCode = await redis.get(`verify_code:${phone}`);
  if (!storedCode || String(storedCode) !== String(verifyCode)) {
    throw new Error('VERIFY_CODE_WRONG');
  }

  // 手机号是否已注册
  const existing = await db.query('SELECT id FROM users WHERE phone = ?', [phone]);
  if (existing.length > 0) {
    throw new Error('PHONE_REGISTERED');
  }

  const hashedPassword = await bcrypt.hash(password, SALT_ROUNDS);

  // 事务：创建用户 + 创建店铺
  const conn = await db.beginTransaction();
  try {
    const userResult = await conn.execute(
      'INSERT INTO users (phone, password, role) VALUES (?, ?, ?)',
      [phone, hashedPassword, 'merchant']
    );
    const userId = userResult.insertId;

    const shopResult = await conn.execute(
      'INSERT INTO shops (user_id, name, status) VALUES (?, ?, ?)',
      [userId, `店铺${userId}`, 'pending']
    );
    const shopId = shopResult.insertId;

    await db.commit(conn);

    // 清除验证码
    await redis.del(`verify_code:${phone}`);

    // 签发 JWT
    const token = jwt.sign(
      { userId, role: 'merchant' },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    logger.info(`商家注册成功: userId=${userId}, shopId=${shopId}`);
    return { userId, shopId, token };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

// ==================== 资质提交 ====================

/**
 * 模拟OCR识别
 */
function simulateOCR(businessLicenseUrl, legalPersonIdUrl) {
  // 生产环境对接真实OCR服务
  if (!businessLicenseUrl || !legalPersonIdUrl) {
    return { ok: false };
  }
  return {
    ok: true,
    data: {
      businessName: '模拟企业名称',
      legalPerson: '模拟法人姓名',
      idNumber: '310***********1234',
      licenseNo: '91310000**********'
    }
  };
}

/**
 * 提交商家资质
 * @param {number} userId
 * @param {string} businessLicense
 * @param {string} legalPersonId
 * @param {string} bankAccount
 * @returns {{ qualificationId: number, ocrResult: object }}
 */
async function submitQualification(userId, businessLicense, legalPersonId, bankAccount) {
  // 查找店铺
  const shops = await db.query('SELECT id, status FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  // 检查是否已有待审核的资质
  const existing = await db.query(
    'SELECT id FROM merchant_qualifications WHERE shop_id = ? AND status = ?',
    [shopId, 'pending']
  );
  if (existing.length > 0) {
    throw new Error('ALREADY_SUBMITTED');
  }

  // OCR识别
  const ocrResult = simulateOCR(businessLicense, legalPersonId);
  if (!ocrResult.ok) {
    throw new Error('OCR_FAIL');
  }

  // 加密银行账户
  const encryptedBank = encrypt(bankAccount);

  // 写入资质记录
  const result = await db.query(
    'INSERT INTO merchant_qualifications (shop_id, business_license, legal_person_id, bank_account) VALUES (?, ?, ?, ?)',
    [shopId, businessLicense, legalPersonId, encryptedBank]
  );

  logger.info(`资质提交成功: shopId=${shopId}, qualificationId=${result.insertId}`);
  return { qualificationId: result.insertId, ocrResult: ocrResult.data };
}

// ==================== 店铺信息 ====================

/**
 * 获取店铺信息
 */
async function getShop(userId) {
  const rows = await db.query(
    'SELECT id, name, logo, description, status, commission_rate, created_at FROM shops WHERE user_id = ?',
    [userId]
  );
  if (rows.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shop = rows[0];
  return {
    id: shop.id,
    name: shop.name,
    logo: shop.logo,
    description: shop.description,
    status: shop.status,
    commissionRate: shop.commission_rate,
    createdAt: shop.created_at
  };
}

/**
 * 更新店铺信息
 */
async function updateShop(userId, data) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }

  const fields = [];
  const values = [];

  if (data.name !== undefined) {
    fields.push('name = ?');
    values.push(data.name.trim());
  }
  if (data.logo !== undefined) {
    fields.push('logo = ?');
    values.push(data.logo);
  }
  if (data.description !== undefined) {
    fields.push('description = ?');
    values.push(data.description);
  }

  if (fields.length === 0) return;

  values.push(shops[0].id);
  await db.query(`UPDATE shops SET ${fields.join(', ')} WHERE id = ?`, values);
  logger.info(`店铺信息更新: shopId=${shops[0].id}`);
}

// ==================== 商品管理 ====================

/**
 * 获取商家商品列表
 */
async function getMerchantProducts(userId, filters = {}) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  const { status, page, pageSize } = filters;
  const offset = (page - 1) * pageSize;

  let whereClause = 'WHERE p.shop_id = ?';
  const params = [shopId];

  if (status) {
    whereClause += ' AND p.status = ?';
    params.push(status);
  }

  const countResult = await db.query(
    `SELECT COUNT(*) as total FROM products p ${whereClause}`,
    params
  );
  const total = countResult[0].total;

  const rows = await db.query(
    `SELECT p.id, p.title, p.description, p.status, p.main_image, p.category_id, p.created_at
     FROM products p ${whereClause}
     ORDER BY p.created_at DESC LIMIT ? OFFSET ?`,
    [...params, pageSize, offset]
  );

  return { list: rows, total, page, pageSize };
}

/**
 * 获取单个商品详情（含SKU）
 */
async function getMerchantProductById(userId, productId) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  const products = await db.query(
    'SELECT id, category_id, title, description, status, main_image, created_at, updated_at FROM products WHERE id = ? AND shop_id = ?',
    [productId, shopId]
  );
  if (products.length === 0) {
    throw new Error('PRODUCT_NOT_FOUND');
  }

  const product = products[0];
  const skus = await db.query(
    'SELECT id, spec_combo, price, stock, image FROM skus WHERE product_id = ?',
    [productId]
  );

  return { ...product, skus };
}

/**
 * 发布商品
 */
async function createProduct(userId, data) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  const { categoryId, title, description, mainImage, skus } = data;

  const conn = await db.beginTransaction();
  try {
    const productResult = await conn.execute(
      'INSERT INTO products (shop_id, category_id, title, description, main_image, status) VALUES (?, ?, ?, ?, ?, ?)',
      [shopId, categoryId, title, description || '', mainImage || '', 'draft']
    );
    const productId = productResult.insertId;

    if (skus && Array.isArray(skus)) {
      for (const sku of skus) {
        await conn.execute(
          'INSERT INTO skus (product_id, spec_combo, price, stock, image) VALUES (?, ?, ?, ?, ?)',
          [productId, sku.specCombo || '', sku.price, sku.stock || 0, sku.image || '']
        );
      }
    }

    await db.commit(conn);
    logger.info(`商品发布: productId=${productId}, shopId=${shopId}`);
    return { productId };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 编辑商品
 */
async function updateMerchantProduct(userId, productId, data) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  // 校验商品属于该店铺
  const products = await db.query(
    'SELECT id FROM products WHERE id = ? AND shop_id = ?',
    [productId, shopId]
  );
  if (products.length === 0) {
    throw new Error('PRODUCT_NOT_FOUND');
  }

  const conn = await db.beginTransaction();
  try {
    const fields = [];
    const values = [];

    if (data.categoryId !== undefined) {
      fields.push('category_id = ?');
      values.push(data.categoryId);
    }
    if (data.title !== undefined) {
      fields.push('title = ?');
      values.push(data.title);
    }
    if (data.description !== undefined) {
      fields.push('description = ?');
      values.push(data.description);
    }
    if (data.mainImage !== undefined) {
      fields.push('main_image = ?');
      values.push(data.mainImage);
    }

    if (fields.length > 0) {
      values.push(productId);
      await conn.execute(
        `UPDATE products SET ${fields.join(', ')} WHERE id = ?`,
        values
      );
    }

    // 更新SKU：先删后插
    if (data.skus !== undefined && Array.isArray(data.skus)) {
      await conn.execute('DELETE FROM skus WHERE product_id = ?', [productId]);
      for (const sku of data.skus) {
        await conn.execute(
          'INSERT INTO skus (product_id, spec_combo, price, stock, image) VALUES (?, ?, ?, ?, ?)',
          [productId, sku.specCombo || '', sku.price, sku.stock || 0, sku.image || '']
        );
      }
    }

    await db.commit(conn);
    logger.info(`商品更新: productId=${productId}`);
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 上架商品
 */
async function listProduct(userId, productId) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  const result = await db.query(
    'UPDATE products SET status = ? WHERE id = ? AND shop_id = ?',
    ['listed', productId, shopId]
  );
  if (!result.affectedRows) {
    throw new Error('PRODUCT_NOT_FOUND');
  }
  logger.info(`商品上架: productId=${productId}`);
}

/**
 * 下架商品
 */
async function delistProduct(userId, productId) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  const result = await db.query(
    'UPDATE products SET status = ? WHERE id = ? AND shop_id = ?',
    ['delisted', productId, shopId]
  );
  if (!result.affectedRows) {
    throw new Error('PRODUCT_NOT_FOUND');
  }
  logger.info(`商品下架: productId=${productId}`);
}

// ==================== 订单 ====================

/**
 * 获取商家订单列表
 */
async function getMerchantOrders(userId, filters = {}) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  const { status, page, pageSize } = filters;
  const offset = (page - 1) * pageSize;

  let whereClause = 'WHERE o.shop_id = ?';
  const params = [shopId];

  if (status) {
    whereClause += ' AND o.status = ?';
    params.push(status);
  }

  const countResult = await db.query(
    `SELECT COUNT(*) as total FROM orders o ${whereClause}`,
    params
  );
  const total = countResult[0].total;

  const rows = await db.query(
    `SELECT o.id, o.order_no, o.user_id, o.total_amount, o.discount_amount, o.pay_amount,
            o.status, o.pay_method, o.pay_time, o.ship_time, o.receive_time, o.created_at
     FROM orders o ${whereClause}
     ORDER BY o.created_at DESC LIMIT ? OFFSET ?`,
    [...params, pageSize, offset]
  );

  return { list: rows, total, page, pageSize };
}

// ==================== 退款 ====================

/**
 * 获取商家退款列表
 */
async function getMerchantRefunds(userId, filters = {}) {
  const shops = await db.query('SELECT id FROM shops WHERE user_id = ?', [userId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }
  const shopId = shops[0].id;

  const { status, page, pageSize } = filters;
  const offset = (page - 1) * pageSize;

  let whereClause = 'WHERE r.merchant_id = ?';
  const params = [shopId];

  if (status) {
    whereClause += ' AND r.status = ?';
    params.push(status);
  }

  const countResult = await db.query(
    `SELECT COUNT(*) as total FROM refunds r ${whereClause}`,
    params
  );
  const total = countResult[0].total;

  const rows = await db.query(
    `SELECT r.id, r.order_id, r.payment_id, r.user_id, r.reason, r.amount, r.status,
            r.apply_at, r.processed_at, r.completed_at, r.created_at
     FROM refunds r ${whereClause}
     ORDER BY r.created_at DESC LIMIT ? OFFSET ?`,
    [...params, pageSize, offset]
  );

  return { list: rows, total, page, pageSize };
}

// ==================== 平台后台：商家审核 ====================

/**
 * 获取商家列表（平台视角）
 */
async function getAdminMerchants(filters = {}) {
  const { status, page, pageSize } = filters;
  const offset = (page - 1) * pageSize;

  let whereClause = '';
  const params = [];

  if (status) {
    whereClause = 'WHERE s.status = ?';
    params.push(status);
  }

  const countResult = await db.query(
    `SELECT COUNT(*) as total FROM shops s ${whereClause}`,
    params
  );
  const total = countResult[0].total;

  const rows = await db.query(
    `SELECT s.id as shopId, s.name as shopName, s.status, s.created_at,
            u.phone,
            mq.status as qualificationStatus
     FROM shops s
     LEFT JOIN users u ON s.user_id = u.id
     LEFT JOIN merchant_qualifications mq ON s.id = mq.shop_id
     ${whereClause}
     ORDER BY s.created_at DESC LIMIT ? OFFSET ?`,
    [...params, pageSize, offset]
  );

  return { list: rows, total, page, pageSize };
}

/**
 * 获取商家详情（含资质信息）
 */
async function getAdminMerchantDetail(shopId) {
  const shops = await db.query(
    `SELECT s.id, s.name, s.logo, s.description, s.status, s.commission_rate, s.created_at,
            u.phone, u.nickname
     FROM shops s
     LEFT JOIN users u ON s.user_id = u.id
     WHERE s.id = ?`,
    [shopId]
  );
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }

  const shop = shops[0];

  const qualifications = await db.query(
    'SELECT id, business_license, legal_person_id, bank_account, status, reviewer_id, review_note, created_at FROM merchant_qualifications WHERE shop_id = ? ORDER BY created_at DESC LIMIT 1',
    [shopId]
  );

  const qualification = qualifications.length > 0 ? qualifications[0] : null;

  return { shop, qualification };
}

/**
 * 审核商家资质
 */
async function reviewQualification(shopId, reviewerId, result, note) {
  // 查找最新一条待审核资质
  const qualifications = await db.query(
    'SELECT id, status FROM merchant_qualifications WHERE shop_id = ? ORDER BY created_at DESC LIMIT 1',
    [shopId]
  );
  if (qualifications.length === 0) {
    throw new Error('QUALIFICATION_NOT_FOUND');
  }

  const qualification = qualifications[0];
  if (qualification.status !== 'pending') {
    throw new Error('ALREADY_REVIEWED');
  }

  // 乐观锁：状态必须为 pending 才更新
  const updateResult = await db.query(
    'UPDATE merchant_qualifications SET status = ?, reviewer_id = ?, review_note = ? WHERE id = ? AND status = ?',
    [result, reviewerId, note || null, qualification.id, 'pending']
  );
  if (!updateResult.affectedRows) {
    throw new Error('ALREADY_REVIEWED');
  }

  logger.info(`资质审核: shopId=${shopId}, result=${result}, reviewerId=${reviewerId}`);
  return { reviewResult: result };
}

/**
 * 激活店铺（资质通过后）
 */
async function activateShop(shopId) {
  const shops = await db.query('SELECT id, status FROM shops WHERE id = ?', [shopId]);
  if (shops.length === 0) {
    throw new Error('SHOP_NOT_FOUND');
  }

  // 检查资质是否已审核通过
  const qualifications = await db.query(
    'SELECT id, status FROM merchant_qualifications WHERE shop_id = ? ORDER BY created_at DESC LIMIT 1',
    [shopId]
  );
  if (qualifications.length === 0 || qualifications[0].status !== 'approved') {
    throw new Error('QUALIFICATION_NOT_APPROVED');
  }

  await db.query('UPDATE shops SET status = ? WHERE id = ?', ['active', shopId]);

  logger.info(`店铺激活: shopId=${shopId}`);
  return { shopStatus: 'active' };
}

module.exports = {
  registerMerchant,
  submitQualification,
  getShop,
  updateShop,
  getMerchantProducts,
  getMerchantProductById,
  createProduct,
  updateMerchantProduct,
  listProduct,
  delistProduct,
  getMerchantOrders,
  getMerchantRefunds,
  getAdminMerchants,
  getAdminMerchantDetail,
  reviewQualification,
  activateShop
};

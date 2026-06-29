const db = require('../config/db');
const { decrypt } = require('../utils/encryption');

/**
 * 根据ID获取用户信息（不含密码，手机号解密）
 * @param {number} id - 用户ID
 * @returns {object} 用户信息 { id, phone, nickname, avatar, role, status, created_at }
 */
async function getUserById(id) {
  const rows = await db.query(
    'SELECT id, phone, nickname, avatar, role, status, created_at FROM users WHERE id = ?',
    [id]
  );
  if (!rows.length) throw new Error('NOT_FOUND');
  const user = rows[0];
  // 解密手机号
  if (user.phone) {
    user.phone = decrypt(user.phone);
  }
  return user;
}

/**
 * 更新用户资料（仅 nickname / avatar）
 * @param {number} id - 用户ID
 * @param {object} data - { nickname?, avatar? }
 * @returns {object} { affectedRows }
 */
async function updateUser(id, data) {
  const fields = [];
  const params = [];

  if (data.nickname !== undefined) {
    fields.push('nickname = ?');
    params.push(data.nickname);
  }
  if (data.avatar !== undefined) {
    fields.push('avatar = ?');
    params.push(data.avatar);
  }

  if (!fields.length) return { affectedRows: 0 };

  params.push(id);
  const result = await db.query(
    `UPDATE users SET ${fields.join(', ')} WHERE id = ?`,
    params
  );
  return { affectedRows: result.affectedRows };
}

/**
 * 获取用户的所有收货地址，默认地址排最前
 * @param {number} userId - 用户ID
 * @returns {array} 地址列表
 */
async function listAddresses(userId) {
  const rows = await db.query(
    'SELECT id, user_id, name, phone, province, city, district, detail, is_default, created_at FROM addresses WHERE user_id = ? ORDER BY is_default DESC, created_at DESC',
    [userId]
  );
  return rows;
}

/**
 * 创建收货地址，若设为默认则先将其他地址取消默认（事务内）
 * @param {number} userId - 用户ID
 * @param {object} data - { name, phone, province, city, district, detail, isDefault }
 * @returns {object} { insertId }
 */
async function createAddress(userId, data) {
  const conn = await db.beginTransaction();
  try {
    // 设为默认地址时，将同用户其他地址取消默认
    if (data.isDefault) {
      await conn.execute(
        'UPDATE addresses SET is_default = 0 WHERE user_id = ?',
        [userId]
      );
    }

    const result = await conn.execute(
      'INSERT INTO addresses (user_id, name, phone, province, city, district, detail, is_default) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      [userId, data.name, data.phone, data.province, data.city, data.district, data.detail, data.isDefault ? 1 : 0]
    );

    await db.commit(conn);
    return { insertId: result.insertId };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 更新收货地址（事务内：校验所有权 → 处理默认 → 更新字段）
 * @param {number} addressId - 地址ID
 * @param {number} userId - 用户ID（权限校验）
 * @param {object} data - { name?, phone?, province?, city?, district?, detail?, isDefault? }
 * @returns {object} { affectedRows }
 */
async function updateAddress(addressId, userId, data) {
  const conn = await db.beginTransaction();
  try {
    // 查询地址并校验所有权
    const [rows] = await conn.execute(
      'SELECT id, user_id FROM addresses WHERE id = ?',
      [addressId]
    );

    if (!rows || !rows.length) {
      await db.rollback(conn);
      throw new Error('NOT_FOUND');
    }

    if (rows[0].user_id !== userId) {
      await db.rollback(conn);
      throw new Error('FORBIDDEN');
    }

    // 设为默认时先取消同用户其他默认
    if (data.isDefault) {
      await conn.execute(
        'UPDATE addresses SET is_default = 0 WHERE user_id = ?',
        [userId]
      );
    }

    // 动态构建 SET 子句
    const fieldMap = {
      name: 'name',
      phone: 'phone',
      province: 'province',
      city: 'city',
      district: 'district',
      detail: 'detail',
      isDefault: 'is_default'
    };

    const setClauses = [];
    const params = [];

    for (const [key, column] of Object.entries(fieldMap)) {
      if (data[key] !== undefined) {
        setClauses.push(`${column} = ?`);
        params.push(key === 'isDefault' ? (data[key] ? 1 : 0) : data[key]);
      }
    }

    if (!setClauses.length) {
      await db.rollback(conn);
      return { affectedRows: 0 };
    }

    params.push(addressId);
    const result = await conn.execute(
      `UPDATE addresses SET ${setClauses.join(', ')} WHERE id = ?`,
      params
    );

    await db.commit(conn);
    return { affectedRows: result.affectedRows };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 删除收货地址（事务内：校验所有权后删除）
 * @param {number} addressId - 地址ID
 * @param {number} userId - 用户ID
 * @returns {object} { affectedRows }
 */
async function deleteAddress(addressId, userId) {
  const conn = await db.beginTransaction();
  try {
    const [rows] = await conn.execute(
      'SELECT id, user_id FROM addresses WHERE id = ?',
      [addressId]
    );

    if (!rows || !rows.length) {
      await db.rollback(conn);
      throw new Error('NOT_FOUND');
    }

    if (rows[0].user_id !== userId) {
      await db.rollback(conn);
      throw new Error('FORBIDDEN');
    }

    const result = await conn.execute(
      'DELETE FROM addresses WHERE id = ?',
      [addressId]
    );

    await db.commit(conn);
    return { affectedRows: result.affectedRows };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

module.exports = {
  getUserById,
  updateUser,
  listAddresses,
  createAddress,
  updateAddress,
  deleteAddress
};

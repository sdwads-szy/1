const db = require('../config/db');

// ── 工具函数 ──

/**
 * 手机号脱敏：138****0001
 */
function maskMobile(mobile) {
  if (!mobile || mobile.length !== 11) return mobile;
  return mobile.slice(0, 3) + '****' + mobile.slice(7);
}

// ── 用户查询 ──

/**
 * 按主键查用户 — db_api_get_user_by_id
 * 返回基本信息，mobile 已脱敏
 */
async function getUserById(userId) {
  const rows = await db.query(
    'SELECT id, mobile, nickname, avatar, role, status, created_at FROM users WHERE id = ?',
    [userId]
  );
  if (!rows.length) {
    throw new Error('USER_NOT_FOUND');
  }
  const user = rows[0];
  user.mobile = maskMobile(user.mobile);
  return user;
}

// ── 用户更新 ──

/**
 * 更新用户昵称/头像 — db_api_update_user
 * 仅更新传入的非 undefined 字段；无有效字段时直接返回
 */
async function updateUser(userId, data) {
  const setClauses = [];
  const params = [];

  if (data.nickname !== undefined) {
    setClauses.push('nickname = ?');
    params.push(data.nickname);
  }
  if (data.avatar !== undefined) {
    setClauses.push('avatar = ?');
    params.push(data.avatar);
  }

  if (setClauses.length === 0) {
    return { userId };
  }

  params.push(userId);
  const result = await db.query(
    `UPDATE users SET ${setClauses.join(', ')} WHERE id = ?`,
    params
  );

  if (result.affectedRows === 0) {
    throw new Error('USER_NOT_FOUND');
  }

  return { userId };
}


// ── 地址查询 ──

/**
 * 获取用户全部收货地址 — db_api_get_addresses_by_user
 * 默认地址排最前，phone 脱敏
 */
async function getAddressesByUserId(userId) {
  const rows = await db.query(
    'SELECT id, province, city, district, detail, phone, contact_name, is_default, created_at FROM user_addresses WHERE user_id = ? ORDER BY is_default DESC, created_at DESC',
    [userId]
  );
  return rows.map(row => ({
    id: row.id,
    province: row.province,
    city: row.city,
    district: row.district,
    detail: row.detail,
    phone: maskMobile(row.phone),
    contactName: row.contact_name,
    isDefault: Boolean(row.is_default),
    createdAt: row.created_at
  }));
}

// ── 地址写操作 ──

/**
 * 新增收货地址 — db_api_create_address
 * 若设默认，事务中先清除该用户其他默认地址
 */
async function createAddress(userId, data) {
  const conn = await db.beginTransaction();
  try {
    // 若设为默认，先取消其他默认
    if (data.isDefault) {
      await conn.execute('UPDATE user_addresses SET is_default = 0 WHERE user_id = ?', [userId]);
    }

    const [result] = await conn.execute(
      'INSERT INTO user_addresses (user_id, province, city, district, detail, phone, contact_name, is_default) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      [userId, data.province, data.city, data.district, data.detail, data.phone, data.contactName, data.isDefault ? 1 : 0]
    );

    await db.commit(conn);
    return { addressId: result.insertId };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 修改收货地址 — db_api_update_address
 * 仅允许修改自己的地址；先校验所有权再更新
 */
async function updateAddress(addressId, userId, data) {
  const conn = await db.beginTransaction();
  try {
    // 所有权校验：地址是否存在 + 是否属于该用户
    const [rows] = await conn.execute(
      'SELECT id, user_id FROM user_addresses WHERE id = ?',
      [addressId]
    );
    if (!rows.length) {
      await db.rollback(conn);
      throw new Error('ADDRESS_NOT_FOUND');
    }
    if (rows[0].user_id !== userId) {
      await db.rollback(conn);
      throw new Error('NOT_OWN_ADDRESS');
    }

    // 若设为默认，先取消该用户其他默认地址
    if (data.isDefault === true) {
      await conn.execute('UPDATE user_addresses SET is_default = 0 WHERE user_id = ?', [userId]);
    }

    // 动态构建 SET 子句：仅更新传入的非 undefined 字段
    const setClauses = [];
    const params = [];

    if (data.province !== undefined) {
      setClauses.push('province = ?');
      params.push(data.province);
    }
    if (data.city !== undefined) {
      setClauses.push('city = ?');
      params.push(data.city);
    }
    if (data.district !== undefined) {
      setClauses.push('district = ?');
      params.push(data.district);
    }
    if (data.detail !== undefined) {
      setClauses.push('detail = ?');
      params.push(data.detail);
    }
    if (data.phone !== undefined) {
      setClauses.push('phone = ?');
      params.push(data.phone);
    }
    if (data.contactName !== undefined) {
      setClauses.push('contact_name = ?');
      params.push(data.contactName);
    }
    if (data.isDefault !== undefined) {
      setClauses.push('is_default = ?');
      params.push(data.isDefault ? 1 : 0);
    }

    if (setClauses.length > 0) {
      params.push(addressId);
      await conn.execute(
        `UPDATE user_addresses SET ${setClauses.join(', ')} WHERE id = ?`,
        params
      );
    }

    await db.commit(conn);
    return { addressId };
  } catch (e) {
    await db.rollback(conn);
    throw e;
  }
}

/**
 * 删除收货地址 — db_api_delete_address
 * 仅允许删除自己的地址；先校验所有权
 */
async function deleteAddress(addressId, userId) {
  // 所有权校验
  const rows = await db.query(
    'SELECT id, user_id FROM user_addresses WHERE id = ?',
    [addressId]
  );
  if (!rows.length) {
    throw new Error('ADDRESS_NOT_FOUND');
  }
  if (rows[0].user_id !== userId) {
    throw new Error('NOT_OWN_ADDRESS');
  }

  await db.query('DELETE FROM user_addresses WHERE id = ?', [addressId]);
  return { addressId };
}

module.exports = {
  getUserById,
  getUserById,
  updateUser,
  getAddressesByUserId,
};

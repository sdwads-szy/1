const response = require('../utils/response');
const userService = require('../services/userService');

/** 手机号脱敏：前三后四，中间用 **** 替代 */
function maskPhone(phone) {
  if (!phone || phone.length < 7) return phone || '';
  return phone.slice(0, 3) + '****' + phone.slice(-4);
}

/** 校验昵称 */
function validateNickname(nickname) {
  if (nickname !== undefined) {
    if (typeof nickname !== 'string' || nickname.trim().length === 0) {
      return '昵称不能为空';
    }
    if (nickname.length > 50) {
      return '昵称不能超过50个字符';
    }
  }
  return null;
}

/** 校验头像 */
function validateAvatar(avatar) {
  if (avatar !== undefined) {
    if (typeof avatar !== 'string' || avatar.length > 255) {
      return '头像地址不合法';
    }
  }
  return null;
}

/** 校验地址字段 */
function validateAddressFields(data, isUpdate) {
  const required = isUpdate ? [] : ['name', 'phone', 'province', 'city', 'district', 'detail'];
  for (const field of required) {
    if (!data[field] || (typeof data[field] === 'string' && data[field].trim().length === 0)) {
      return `${field} 不能为空`;
    }
  }
  if (data.name !== undefined && (typeof data.name !== 'string' || data.name.length > 50)) {
    return '收货人姓名不能超过50个字符';
  }
  if (data.phone !== undefined && (typeof data.phone !== 'string' || data.phone.length > 20)) {
    return '联系电话不能超过20个字符';
  }
  if (data.province !== undefined && (typeof data.province !== 'string' || data.province.length > 50)) {
    return '省份不能超过50个字符';
  }
  if (data.city !== undefined && (typeof data.city !== 'string' || data.city.length > 50)) {
    return '城市不能超过50个字符';
  }
  if (data.district !== undefined && (typeof data.district !== 'string' || data.district.length > 50)) {
    return '区县不能超过50个字符';
  }
  if (data.detail !== undefined && (typeof data.detail !== 'string' || data.detail.length > 255)) {
    return '详细地址不能超过255个字符';
  }
  return null;
}

/**
 * GET /api/user/profile — 获取个人信息
 */
async function getProfile(req, res) {
  try {
    const user = await userService.getUserById(req.userId);
    response.success(res, {
      nickname: user.nickname,
      avatar: user.avatar,
      phone: maskPhone(user.phone),
      role: user.role
    }, '获取成功');
  } catch (e) {
    if (e.message === 'NOT_FOUND') {
      return response.fail(res, '用户不存在', 404);
    }
    response.error(res, '服务器错误');
  }
}

/**
 * PUT /api/user/profile — 更新个人信息
 */
async function updateProfile(req, res) {
  try {
    const { nickname, avatar } = req.body;

    // 必须至少提供一个字段
    if (nickname === undefined && avatar === undefined) {
      return response.fail(res, '请提供需要修改的字段', 400);
    }

    // 校验
    const nicknameErr = validateNickname(nickname);
    if (nicknameErr) return response.fail(res, nicknameErr, 400);

    const avatarErr = validateAvatar(avatar);
    if (avatarErr) return response.fail(res, avatarErr, 400);

    // 构建更新数据
    const updateData = {};
    if (nickname !== undefined) updateData.nickname = nickname.trim();
    if (avatar !== undefined) updateData.avatar = avatar.trim();

    await userService.updateUser(req.userId, updateData);
    response.success(res, { success: true }, '更新成功');
  } catch (e) {
    if (e.message === 'NOT_FOUND') {
      return response.fail(res, '用户不存在', 404);
    }
    response.error(res, '服务器错误');
  }
}

/**
 * GET /api/user/addresses — 获取收货地址列表
 */
async function listAddresses(req, res) {
  try {
    const addresses = await userService.listAddresses(req.userId);
    // 转换 is_default 字段名为 isDefault（前端期望驼峰）
    const list = addresses.map(addr => ({
      id: addr.id,
      name: addr.name,
      phone: addr.phone,
      province: addr.province,
      city: addr.city,
      district: addr.district,
      detail: addr.detail,
      isDefault: !!addr.is_default
    }));
    response.success(res, list, '获取成功');
  } catch (e) {
    response.error(res, '服务器错误');
  }
}

/**
 * POST /api/user/addresses — 创建收货地址
 */
async function createAddress(req, res) {
  try {
    const validationErr = validateAddressFields(req.body, false);
    if (validationErr) return response.fail(res, validationErr, 400);

    const { name, phone, province, city, district, detail, isDefault } = req.body;

    const result = await userService.createAddress(req.userId, {
      name: name.trim(),
      phone: phone.trim(),
      province: province.trim(),
      city: city.trim(),
      district: district.trim(),
      detail: detail.trim(),
      isDefault: !!isDefault
    });

    response.success(res, { id: result.insertId }, '创建成功');
  } catch (e) {
    response.error(res, '服务器错误');
  }
}

/**
 * PUT /api/user/addresses/:id — 更新收货地址
 */
async function updateAddress(req, res) {
  try {
    const addressId = parseInt(req.params.id) || 0;
    if (!addressId) return response.fail(res, '地址ID不合法', 400);

    const validationErr = validateAddressFields(req.body, true);
    if (validationErr) return response.fail(res, validationErr, 400);

    const { name, phone, province, city, district, detail, isDefault } = req.body;

    const updateData = {};
    if (name !== undefined) updateData.name = name.trim();
    if (phone !== undefined) updateData.phone = phone.trim();
    if (province !== undefined) updateData.province = province.trim();
    if (city !== undefined) updateData.city = city.trim();
    if (district !== undefined) updateData.district = district.trim();
    if (detail !== undefined) updateData.detail = detail.trim();
    if (isDefault !== undefined) updateData.isDefault = !!isDefault;

    if (Object.keys(updateData).length === 0) {
      return response.fail(res, '请提供需要修改的字段', 400);
    }

    await userService.updateAddress(addressId, req.userId, updateData);
    response.success(res, { success: true }, '更新成功');
  } catch (e) {
    if (e.message === 'NOT_FOUND') {
      return response.fail(res, '地址不存在', 404);
    }
    if (e.message === 'FORBIDDEN') {
      return response.fail(res, '无权操作该地址', 403);
    }
    response.error(res, '服务器错误');
  }
}

/**
 * DELETE /api/user/addresses/:id — 删除收货地址
 */
async function deleteAddress(req, res) {
  try {
    const addressId = parseInt(req.params.id) || 0;
    if (!addressId) return response.fail(res, '地址ID不合法', 400);

    await userService.deleteAddress(addressId, req.userId);
    response.success(res, { success: true }, '删除成功');
  } catch (e) {
    if (e.message === 'NOT_FOUND') {
      return response.fail(res, '地址不存在', 404);
    }
    if (e.message === 'FORBIDDEN') {
      return response.fail(res, '无权操作该地址', 403);
    }
    response.error(res, '服务器错误');
  }
}

module.exports = {
  getProfile,
  updateProfile,
  listAddresses,
  createAddress,
  updateAddress,
  deleteAddress
};

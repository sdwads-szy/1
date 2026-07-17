const response = require('../utils/response');
const userService = require('../services/userService');

/**
 * GET /api/user/profile
 * 获取当前登录用户基本信息（手机号脱敏）
 */
async function getUserProfile(req, res) {
  try {
    const user = await userService.getUserById(req.userId);
    response.success(res, {
      userId: user.id,
      mobile: user.mobile,
      nickname: user.nickname,
      avatar: user.avatar,
      role: user.role
    });
  } catch (e) {
    if (e.message === 'UNAUTHORIZED') {
      response.fail(res, '未登录或登录已过期', 401);
    } else if (e.message === 'USER_NOT_FOUND') {
      response.fail(res, '用户不存在', 404);
    } else {
      response.error(res, e.message);
    }
  }
}

/**
 * PUT /api/user/profile
 * 修改当前用户昵称/头像
 */
async function updateProfile(req, res) {
  try {
    const { nickname, avatar } = req.body;
    if (!nickname && !avatar) {
      return response.fail(res, '至少传入 nickname 或 avatar', 400);
    }
    await userService.updateUser(req.userId, { nickname, avatar });
    response.success(res, { userId: req.userId, nickname, avatar });
  } catch (e) {
    if (e.message === 'USER_NOT_FOUND') {
      response.fail(res, '用户不存在', 404);
    } else {
      response.error(res, e.message);
    }
  }
}


/**
 * GET /api/user/addresses
 * 获取当前用户所有收货地址（默认地址排最前，手机号脱敏）
 */
async function getAddresses(req, res) {
  try {
    const list = await userService.getAddressesByUserId(req.userId);
    response.success(res, { list });
  } catch (e) {
    response.error(res, e.message);
  }
}

/**
 * POST /api/user/addresses
 * 新增收货地址
 */
async function createAddress(req, res) {
  try {
    const { province, city, district, detail, phone, contactName, isDefault } = req.body;

    // 必填校验
    if (!province || !city || !district || !detail || !phone || !contactName) {
      return response.fail(res, '缺少必填字段', 400);
    }

    // 手机号格式校验
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      return response.fail(res, '手机号格式不正确', 422);
    }

    const result = await userService.createAddress(req.userId, {
      province,
      city,
      district,
      detail,
      phone,
      contactName,
      isDefault: isDefault || false
    });
    response.success(res, { addressId: result.addressId });
  } catch (e) {
    response.error(res, e.message);
  }
}

/**
 * PUT /api/user/addresses/:id
 * 修改收货地址（仅允许修改自己的地址）
 */
async function updateAddress(req, res) {
  try {
    const addressId = parseInt(req.params.id, 10);
    if (!addressId || addressId < 1) {
      return response.fail(res, '无效的地址ID', 400);
    }

    const { province, city, district, detail, phone, contactName, isDefault } = req.body;

    // 手机号格式校验（若传入）
    if (phone !== undefined && !/^1[3-9]\d{9}$/.test(phone)) {
      return response.fail(res, '手机号格式不正确', 422);
    }

    await userService.updateAddress(addressId, req.userId, {
      province,
      city,
      district,
      detail,
      phone,
      contactName,
      isDefault
    });
    response.success(res, { addressId });
  } catch (e) {
    if (e.message === 'ADDRESS_NOT_FOUND') {
      response.fail(res, '地址不存在', 404);
    } else if (e.message === 'FORBIDDEN_NOT_OWNER') {
      response.fail(res, '无权操作此地址', 403);
    } else {
      response.error(res, e.message);
    }
  }
}

/**
 * DELETE /api/user/addresses/:id
 * 删除收货地址（仅允许删除自己的地址）
 */
async function deleteAddress(req, res) {
  try {
    const addressId = parseInt(req.params.id, 10);
    if (!addressId || addressId < 1) {
      return response.fail(res, '无效的地址ID', 400);
    }

    await userService.deleteAddress(addressId, req.userId);
    response.success(res, null);
  } catch (e) {
    if (e.message === 'ADDRESS_NOT_FOUND') {
      response.fail(res, '地址不存在', 404);
    } else if (e.message === 'FORBIDDEN_NOT_OWNER') {
      response.fail(res, '无权操作此地址', 403);
    } else {
      response.error(res, e.message);
    }
  }
}

module.exports = {
  getUserProfile,
  updateProfile,
  getAddresses,
  createAddress,
  updateAddress,
  deleteAddress
};

const response = require('../utils/response');
const merchantRegisterService = require('../services/merchantRegisterService');

/**
 * 商家入驻申请：分步提交入驻资料
 * POST /api/merchants/register
 */
async function applyMerchant(req, res) {
  try {
    const { mobile, code: smsCode, creditCode: credit_code, bizLicense: biz_license, shopName: shop_name, contact_name, contact_mobile, logo } = req.body;

    // 基础校验
    if (!mobile || !/^1[3-9]\d{9}$/.test(mobile)) {
      return response.fail(res, '手机号格式不正确', 400);
    }
    if (!smsCode || !/^\d{6}$/.test(smsCode)) {
      return response.fail(res, '验证码格式不正确', 400);
    }
    if (!credit_code || !/^[A-Z0-9]{18}$/.test(credit_code)) {
      return response.fail(res, '统一社会信用代码格式不正确', 400);
    }
    if (!biz_license || biz_license.length < 1) {
      return response.fail(res, '请上传营业执照', 400);
    }
    if (!shop_name || shop_name.length < 2 || shop_name.length > 64) {
      return response.fail(res, '店铺名称长度需在2~64字符之间', 400);
    }
    if (!contact_name || contact_name.length < 1) {
      return response.fail(res, '联系人姓名不能为空', 400);
    }
    if (!contact_mobile || !/^1[3-9]\d{9}$/.test(contact_mobile)) {
      return response.fail(res, '联系人手机号格式不正确', 400);
    }

    const result = await merchantRegisterService.registerMerchant(
      req.userId, mobile, smsCode, credit_code, biz_license,
      contact_name, contact_mobile, shop_name, logo || null
    );

    return response.success(res, result, '入驻申请已提交');
  } catch (e) {
    const errorMap = {
      SMS_CODE_ERROR: { status: 400, message: '短信验证码错误' },
      INVALID_CODE: { status: 400, message: '验证码无效' },
      CODE_EXPIRED: { status: 400, message: '验证码已过期' },
      CREDIT_CODE_DUPLICATE: { status: 422, message: '该统一社会信用代码已被注册' },
      DUPLICATE_CREDIT_CODE: { status: 422, message: '该统一社会信用代码已被注册' },
      DUPLICATE_SHOP_NAME: { status: 422, message: '店铺名已被占用' },
    };

    const mapped = errorMap[e.message];
    if (mapped) {
      return response.fail(res, mapped.message, mapped.status);
    }

    // ER_DUP_ENTRY from MySQL unique constraint — 兜底处理
    if (e.code === 'ER_DUP_ENTRY') {
      if (e.sqlMessage && e.sqlMessage.includes('credit_code')) {
        return response.fail(res, '该统一社会信用代码已被注册', 422);
      }
      if (e.sqlMessage && (e.sqlMessage.includes('shops.name') || e.sqlMessage.includes('name'))) {
        return response.fail(res, '店铺名已被占用', 422);
      }
      return response.fail(res, '数据重复，请检查后重试', 422);
    }

    return response.error(res, '入驻申请失败');
  }
}

/**
 * 查询入驻审核状态
 * GET /api/merchants/register/status
 */
async function getStatus(req, res) {
  try {
    const result = await merchantRegisterService.getRegisterStatus(req.userId);
    return response.success(res, result);
  } catch (e) {
    if (e.message === 'NO_APPLICATION') {
      return response.fail(res, '未找到入驻申请记录', 404);
    }
    return response.error(res, '查询失败');
  }
}

module.exports = { applyMerchant, getStatus };

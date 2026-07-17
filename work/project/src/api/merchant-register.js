import request from '@/utils/request';

/**
 * 发送短信验证码
 * @param {Object} data - { mobile }
 * @returns {Promise}
 */
export function sendSmsCode(data) {
  return request({ url: '/sms/send', method: 'post', data });
}

/**
 * 提交入驻申请（分步表单汇总提交）
 * @param {Object} data - { mobile, code, creditCode, bizLicense, shopName, logo? }
 * @returns {Promise}
 */
export function submitMerchantRegister(data) {
  return request({ url: '/merchants/register', method: 'post', data });
}

/**
 * 查询入驻审核状态
 * @returns {Promise}
 */
export function getRegisterStatus() {
  return request({ url: '/merchants/register/status', method: 'get' });
}

/**
 * 上传文件
 * @param {FormData} formData
 * @returns {Promise}
 */
export function uploadFile(formData) {
  return request({
    url: '/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

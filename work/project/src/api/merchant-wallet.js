import request from '@/utils/request';

/**
 * 获取商家钱包余额
 * @returns {Promise} { balance, frozenBalance, totalEarned }
 */
export function getMerchantWallet() {
  return request({ url: '/merchant/wallet', method: 'get' });
}

// @api 平台后台 - 商品审核管理
import request from '@/utils/request';

const BASE = '/admin/products';

/** 获取商品审核列表（可按状态筛选） */
export function getAuditList(data) {
  return request({ url: BASE, method: 'get', params: data });
}

/** 获取商品审核详情（含SKU、快照、审核日志） */
export function getAuditDetail(id) {
  return request({ url: `${BASE}/${id}`, method: 'get' });
}

/** 审核商品（通过/驳回） */
export function reviewProduct(id, data) {
  return request({ url: `${BASE}/${id}/review`, method: 'put', data });
}

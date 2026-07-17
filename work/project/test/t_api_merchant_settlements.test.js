const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_merchant_settlements', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/merchantWallet.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/merchantWalletController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/merchant-settlements.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET /settlements → handler: listSettlements', () => {
      expect(routeSrc).toContain('/settlements');
      expect(ctrlSrc).toContain('listSettlements');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('controller 接收了预期字段: page, pageSize', () => {
      ['page', 'pageSize'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链（auth category）====
  describe('中间件链', () => {
    it('GET /settlements 挂载 authenticate + requireRole 中间件', () => {
      expect(routeSrc).toContain('authenticate');
      expect(routeSrc).toContain('requireRole');
      expect(routeSrc).toContain('merchant');
    });
  });

  // ==== 维度4: 错误码映射（error category）====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['FORBIDDEN'];
      codes.forEach(c => expect(ctrlSrc).toContain(c));
    });
  });

  // ==== 维度5: 响应格式 ====
  describe('响应格式', () => {
    it('controller 使用规范响应方法', () => {
      const usesResponse = ctrlSrc.includes('response.success')
                        || ctrlSrc.includes('response.fail')
                        || ctrlSrc.includes('response.error')
                        || ctrlSrc.includes('res.json(')
                        || ctrlSrc.includes('res.status(');
      expect(usesResponse).toBe(true);
    });
  });

  // ==== 维度6: 前端对齐 ====
  describe('前端对齐', () => {
    it('前端 API 调用的端点与后端路由一致', () => {
      expect(frontSrc).toContain('/merchant/settlements');
      expect(frontSrc).toContain('getMerchantSettlements');
    });
  });
});

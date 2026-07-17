const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_merchant_refunds', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/merchantRefunds.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/merchantRefundController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/merchant-refunds.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: listShopRefunds', () => {
      expect(routeSrc).toContain('listShopRefunds');
      expect(ctrlSrc).toContain('listShopRefunds');
    });
    it('PUT /:id/review → handler: reviewRefund', () => {
      expect(routeSrc).toContain('/:id/review');
      expect(routeSrc).toContain('reviewRefund');
      expect(ctrlSrc).toContain('reviewRefund');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('reviewRefund 接收了预期字段: id, action, reason', () => {
      ['id', 'action', 'reason'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链（auth category）====
  describe('中间件链', () => {
    it('所有路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it("所有路由挂载了 requireRole(['merchant']) 中间件", () => {
      expect(routeSrc).toContain("requireRole(['merchant'])");
    });
  });

  // ==== 维度4: 错误码映射（error category）====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['NOT_YOUR_REFUND', 'ALREADY_REVIEWED'];
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
    it('前端 API 文件导出 getMerchantRefunds 与 approveRefund', () => {
      expect(frontSrc).toContain('getMerchantRefunds');
      expect(frontSrc).toContain('approveRefund');
    });
    it('前端 API 调用的 URL 与契约一致', () => {
      expect(frontSrc).toContain('/merchant/refunds');
      expect(frontSrc).toContain('approve');
    });
  });
});

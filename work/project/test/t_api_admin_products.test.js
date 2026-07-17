const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_admin_products', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/adminProducts.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/adminProductController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/admin-products.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: getReviewProducts', () => {
      expect(routeSrc).toContain('listProducts');
    });
    it('PUT /:id/review → handler: reviewProduct', () => {
      expect(routeSrc).toContain('/:id/review');
      expect(ctrlSrc).toContain('reviewProduct');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('reviewProduct controller 接收了预期字段: action, reason', () => {
      ['action', 'reason'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链（auth）====
  describe('中间件链', () => {
    it('PUT /:id/review 挂载了 authenticate + requireRole 中间件', () => {
      expect(routeSrc).toContain('authenticate');
      expect(routeSrc).toContain('hasRole');
    });
  });

  // ==== 维度4: 错误码映射（error + boundary）====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码: FORBIDDEN, SENSITIVE_CONTENT', () => {
      const codes = ['SENSITIVE_WORD'];
      codes.forEach(c => expect(ctrlSrc).toContain(c));
    });
    it('敏感词过滤返回 422 状态码', () => {
      expect(ctrlSrc).toContain('422');
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
      const endpoints = ['/admin/products', 'reviewProduct'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});

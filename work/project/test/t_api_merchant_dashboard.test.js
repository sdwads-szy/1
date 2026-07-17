const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_merchant_dashboard', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/merchantDashboard.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/merchantDashboardController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/merchant-dashboard.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: getMerchantDashboard', () => {
      expect(routeSrc).toContain('/');
      expect(ctrlSrc).toContain('getMerchantDashboard');
    });
  });

  // ==== 维度3: 中间件链（auth category）====
  describe('中间件链', () => {
    it('路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it("路由挂载了 hasRole('merchant') 中间件", () => {
      expect(routeSrc).toContain('hasRole');
      expect(routeSrc).toContain('merchant');
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
      expect(frontSrc).toContain('/merchant/dashboard');
      expect(frontSrc).toContain('getMerchantDashboard');
    });
  });
});

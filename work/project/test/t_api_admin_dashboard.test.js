const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_admin_dashboard', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/adminDashboard.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/adminDashboardController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/admin-dashboard.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it("GET / → handler: getAdminDashboard", () => {
      expect(routeSrc).toContain('/');
      expect(routeSrc).toContain('getAdminDashboard');
      expect(ctrlSrc).toContain('getAdminDashboard');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('controller 引用了 dashboard 统计字段', () => {
      // 来源: t_dbapi_stats → adminDashboardService.getAdminDashboard → platform_daily_stats 列
      ['gmv', 'order_count', 'stat_date', 'paid_order_count', 'refund_rate', 'commission'].forEach(f => {
        expect(ctrlSrc).toContain(f);
      });
    });
  });

  // ==== 维度3: 中间件链（auth category）====
  describe('中间件链', () => {
    it('路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it("路由挂载了 requireRole 中间件，限定 admin 角色", () => {
      expect(routeSrc).toContain('requireRole');
      expect(routeSrc).toContain('admin');
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
      // 来源: t_frontend_admin_dashboard → api_calls: { getAdminDashboard: "GET /admin/dashboard" }
      const endpoints = ['getAdminDashboard', '/admin/dashboard'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});

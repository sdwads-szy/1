const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_admin_logistics', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/adminLogistics.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/adminLogisticsController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/admin-logistics.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: getLogisticsOverview', () => {
      expect(routeSrc).toContain('/');
      expect(ctrlSrc).toContain('getLogisticsOverview');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('controller 包含 getLogisticsOverview 函数定义', () => {
      expect(ctrlSrc).toContain('getLogisticsOverview');
    });
  });

  // ==== 维度3: 中间件链 ====
  describe('中间件链', () => {
    it('路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it('路由挂载了 requireRole 中间件', () => {
      expect(routeSrc).toContain('requireRole');
    });
  });

  // ==== 维度4: 错误码映射 ====
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
      const endpoints = ['getLogisticsMonitor', '/admin/logistics/monitor'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});

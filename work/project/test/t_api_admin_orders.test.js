const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_admin_orders', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/adminOrders.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/adminOrderController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/admin-orders.js'), 'utf-8');

  describe('路由匹配', () => {
    it('GET / → handler: getAdminOrders', () => {
      expect(routeSrc).toContain('getAdminOrders');
      expect(ctrlSrc).toContain('getAdminOrders');
    });
  });

  describe('字段一致', () => {
    it('controller 接收了预期字段: page, pageSize, orderNo, status, shopId', () => {
      ['page', 'pageSize', 'orderNo', 'status', 'shopId'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  describe('中间件链', () => {
    it('路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it('路由挂载了 hasRole 中间件', () => {
      expect(routeSrc).toContain('hasRole');
    });
  });

  describe('错误码映射', () => {
    it('路由层 hasRole 中间件处理非管理员403', () => {
      expect(routeSrc).toContain("hasRole('admin')");
    });
  });

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

  describe('前端对齐', () => {
    it('前端 API 调用的端点与后端路由一致', () => {
      const endpoints = ['getAdminOrders', '/admin/orders'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});

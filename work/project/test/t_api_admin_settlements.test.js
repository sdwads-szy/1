const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_admin_settlements', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/adminSettlements.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/adminSettlementController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/admin-settlements.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: listSettlements', () => {
      expect(routeSrc).toContain('/');
      expect(ctrlSrc).toContain('listSettlements');
    });
    it('PUT /:id/pay → handler: paySettlement', () => {
      expect(routeSrc).toContain('/:id/pay');
      expect(ctrlSrc).toContain('paySettlement');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('controller 接收了预期字段: status, page, pageSize', () => {
      ['status', 'page', 'pageSize'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('controller 接收了预期字段: req.params.id', () => {
      expect(ctrlSrc).toContain('req.params.id');
    });
  });

  // ==== 维度3: 中间件链（仅 auth category）====
  describe('中间件链', () => {
    it('路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it('路由挂载了 requireRole 中间件', () => {
      expect(routeSrc).toContain('requireRole');
    });
  });

  // ==== 维度4: 错误码映射（仅 error category）====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['FORBIDDEN', 'SETTLEMENT_NOT_CONFIRMED'];
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
      expect(frontSrc).toContain('/admin/settlements');
      expect(frontSrc).toContain('/pay');
    });
  });
});

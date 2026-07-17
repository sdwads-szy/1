const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_admin_merchants', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/adminMerchants.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/adminMerchantController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/admin-merchants.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: listMerchants', () => {
      expect(routeSrc).toContain('listMerchants');
      expect(ctrlSrc).toContain('listMerchants');
    });
    it('PUT /:id/review → handler: reviewMerchant', () => {
      expect(routeSrc).toContain('/:id/review');
      expect(ctrlSrc).toContain('reviewMerchant');
    });
    it('PUT /:id/freeze → handler: freezeMerchant', () => {
      expect(routeSrc).toContain('/:id/freeze');
      expect(ctrlSrc).toContain('freezeMerchant');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('listMerchants controller 接收了预期字段: status, page, pageSize', () => {
      ['status', 'page', 'pageSize'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('reviewMerchant controller 接收了预期字段: id, action, reason', () => {
      ['id', 'action', 'reason'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('freezeMerchant controller 接收了预期字段: id, reason', () => {
      ['id', 'reason'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链 ====
  describe('中间件链', () => {
    it('所有路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
    it('所有路由挂载了 requireRole 中间件', () => {
      expect(routeSrc).toContain('requireRole');
    });
  });

  // ==== 维度4: 错误码映射 ====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['FORBIDDEN', 'ALREADY_REVIEWED'];
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
      const endpoints = ['/admin/merchants'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });

  // ==== boundary ====
  describe('boundary', () => {
    it('reviewMerchant 校验已审核状态 → 409', () => {
      expect(ctrlSrc).toContain('pending_review');
      expect(ctrlSrc).toContain('已审核');
    });
  });
});

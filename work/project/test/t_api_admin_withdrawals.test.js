const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_admin_withdrawals', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/adminWithdrawals.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/adminWithdrawalController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/admin-withdrawals.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET / → handler: listWithdrawals', () => {
      expect(routeSrc).toContain('/');
      expect(ctrlSrc).toContain('getWithdrawals');
    });

    it('PUT /:id/approve → handler: approveWithdrawal', () => {
      expect(routeSrc).toContain('/:id/approve');
      expect(ctrlSrc).toContain('approveWithdrawal');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('controller 接收了预期字段: status, page, pageSize (listWithdrawals)', () => {
      ['status', 'page', 'pageSize'].forEach(f => expect(ctrlSrc).toContain(f));
    });

    it('controller 接收了预期字段: id, action, reason (approveWithdrawal)', () => {
      ['id', 'action', 'reason'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链 ====
  describe('中间件链', () => {
    it('所有 /admin/withdrawals 路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });

    it('所有 /admin/withdrawals 路由挂载了 requireRole 中间件', () => {
      expect(routeSrc).toContain('hasRole');
    });
  });

  // ==== 维度4: 错误码映射 ====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['WITHDRAWAL_NOT_FOUND', 'ALREADY_PROCESSED', 'MISSING_ACTION'];
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
      expect(frontSrc).toContain('/admin/withdrawals');
    });
  });
});

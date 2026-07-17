const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_user_addresses', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/user.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/userController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/user.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET /addresses → handler: listAddresses', () => {
      expect(routeSrc).toContain('/addresses');
      expect(ctrlSrc).toContain('getAddresses');
    });
    it('POST /addresses → handler: createAddress', () => {
      expect(routeSrc).toContain('/addresses');
      expect(ctrlSrc).toContain('createAddress');
    });
    it('PUT /addresses/:id → handler: updateAddress', () => {
      expect(routeSrc).toContain('/addresses/:id');
      expect(ctrlSrc).toContain('updateAddress');
    });
    it('DELETE /addresses/:id → handler: deleteAddress', () => {
      expect(routeSrc).toContain('/addresses/:id');
      expect(ctrlSrc).toContain('deleteAddress');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('createAddress controller 接收了预期字段: province, city, district, detail, phone, contact_name, is_default', () => {
      ['province', 'city', 'district', 'detail', 'phone', 'contactName', 'isDefault'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('updateAddress controller 接收了预期字段: id, province, city, district, detail, phone, contact_name, is_default', () => {
      ['id', 'province', 'city', 'district', 'detail', 'phone', 'contactName', 'isDefault'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链 ====
  describe('中间件链', () => {
    it('所有地址路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
      const routeLines = routeSrc.split('\n').filter(l => l.includes('/addresses') && l.includes('router.'));
      expect(routeLines.length).toBeGreaterThanOrEqual(4);
      routeLines.forEach(line => {
        expect(line).toContain('authenticate');
      });
    });
  });

  // ==== 维度4: 错误码映射 ====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['FORBIDDEN_NOT_OWNER', 'ADDRESS_NOT_FOUND'];
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
      const endpoints = ['/user/addresses'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
      const functions = ['getAddresses', 'createAddress', 'updateAddress', 'deleteAddress'];
      functions.forEach(fn => expect(frontSrc).toContain(fn));
    });
  });
});

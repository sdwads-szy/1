const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_user_profile', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/user.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/userController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/user.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('GET /profile → handler: getProfile', () => {
      expect(routeSrc).toContain('/profile');
      expect(routeSrc).toContain('getProfile');
    });
    it('PUT /profile → handler: updateProfile', () => {
      expect(routeSrc).toContain('/profile');
      expect(ctrlSrc).toContain('updateProfile');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('controller 接收了预期字段: nickname, avatar', () => {
      ['nickname', 'avatar'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链 ====
  describe('中间件链', () => {
    it('所有 /profile 路由挂载了 authenticate 中间件', () => {
      expect(routeSrc).toContain('authenticate');
    });
  });

  // ==== 维度4: 错误码映射 ====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['UNAUTHORIZED', 'USER_NOT_FOUND'];
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
      const endpoints = ['/user/profile', 'getUserProfile', 'getAddresses', 'createAddress', 'updateAddress', 'deleteAddress'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});

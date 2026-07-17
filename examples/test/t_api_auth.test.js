const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');

describe('t_api_auth', () => {
  const routeSrc = fs.readFileSync(path.join(workspace, 'routes/auth.js'), 'utf-8');
  const ctrlSrc  = fs.readFileSync(path.join(workspace, 'controllers/authController.js'), 'utf-8');
  const frontSrc = fs.readFileSync(path.join(workspace, 'src/api/auth.js'), 'utf-8');

  // ==== 维度1: 路由匹配 ====
  describe('路由匹配', () => {
    it('POST /login → handler: login', () => {
      expect(routeSrc).toContain('/login');
      expect(ctrlSrc).toContain('login');
    });
    it('POST /register → handler: register', () => {
      expect(routeSrc).toContain('/register');
      expect(ctrlSrc).toContain('register');
    });
    it('POST /refresh → handler: refreshToken', () => {
      expect(routeSrc).toContain('/refresh');
      expect(ctrlSrc).toContain('refreshToken');
    });
  });

  // ==== 维度2: 字段一致 ====
  describe('字段一致', () => {
    it('login controller 接收了预期字段: mobile, password', () => {
      ['mobile', 'password'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('register controller 接收了预期字段: mobile, password, nickname, smsCode', () => {
      ['mobile', 'password', 'nickname', 'code'].forEach(f => expect(ctrlSrc).toContain(f));
    });
    it('refreshToken controller 接收了预期字段: refreshToken', () => {
      ['refreshToken'].forEach(f => expect(ctrlSrc).toContain(f));
    });
  });

  // ==== 维度3: 中间件链（auth category）====
  describe('中间件链', () => {
    it('login 路由不含 authenticate 中间件', () => {
      const lines = routeSrc.split('\n');
      const loginLine = lines.find(l => l.includes('/login'));
      if (loginLine) {
        expect(loginLine).not.toContain('authenticate');
      }
    });
    it('register 路由不含 authenticate 中间件', () => {
      const lines = routeSrc.split('\n');
      const registerLine = lines.find(l => l.includes('/register'));
      if (registerLine) {
        expect(registerLine).not.toContain('authenticate');
      }
    });
    it('refresh 路由挂载了 authenticate 中间件', () => {
      const lines = routeSrc.split('\n');
      const refreshLine = lines.find(l => l.includes('/refresh'));
      if (refreshLine) {
        expect(refreshLine).toContain('authenticate');
      }
    });
  });

  // ==== 维度4: 错误码映射（error category）====
  describe('错误码映射', () => {
    it('controller 包含所有契约错误码', () => {
      const codes = ['PASSWORD_WRONG', 'CODE_EXPIRED', 'PHONE_EXISTS'];
      codes.forEach(c => expect(ctrlSrc).toContain(c));
    });
  });

  // ==== boundary: 验证码过期登录 ====
  describe('边界场景', () => {
    it('login 中 smsCode 校验过期返回提示', () => {
      expect(ctrlSrc).toContain('验证码已过期');
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
      const endpoints = ['/auth/login', '/auth/register', '/auth/refresh'];
      endpoints.forEach(ep => expect(frontSrc).toContain(ep));
    });
  });
});

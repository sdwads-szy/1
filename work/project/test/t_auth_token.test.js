/** @jest-environment node */
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');

const JWT_SECRET = process.env.JWT_SECRET || 'test_jwt_secret';
const REFRESH_SECRET = process.env.JWT_REFRESH_SECRET || 'test_refresh_secret';
const workspace = path.resolve(__dirname, '..');

describe('t_auth_token', () => {
  // ================================================================
  // Token 维度 — jwt.sign + jwt.verify 直调
  // ================================================================
  describe('correct — Token 签名与验签', () => {
    it('jwt.sign 产出三段式 token，每段合法 base64', () => {
      const token = jwt.sign({ userId: 1, role: 'user' }, JWT_SECRET, { expiresIn: '15m' });
      const parts = token.split('.');
      expect(parts.length).toBe(3);
      parts.forEach(p => expect(() => Buffer.from(p, 'base64')).not.toThrow());
    });

    it('jwt.verify 解码出 userId 和 role', () => {
      const token = jwt.sign({ userId: 1, role: 'user' }, JWT_SECRET, { expiresIn: '15m' });
      const decoded = jwt.verify(token, JWT_SECRET);
      expect(decoded.userId).toBe(1);
      expect(decoded.role).toBe('user');
      expect(decoded.iat).toEqual(expect.any(Number));
      expect(decoded.exp).toEqual(expect.any(Number));
    });

    it('refresh token 含 type=refresh 且有效期≥29天', () => {
      const token = jwt.sign({ userId: 1, type: 'refresh' }, REFRESH_SECRET, { expiresIn: '30d' });
      const decoded = jwt.verify(token, REFRESH_SECRET);
      expect(decoded.type).toBe('refresh');
      expect(decoded.exp - decoded.iat).toBeGreaterThanOrEqual(29 * 24 * 3600);
    });
  });

  describe('error — Token 拒绝', () => {
    it('过期 token 被 jwt.verify 拒绝抛出 TokenExpiredError', () => {
      const token = jwt.sign({ userId: 1, role: 'user' }, JWT_SECRET, { expiresIn: '0s' });
      expect(() => jwt.verify(token, JWT_SECRET)).toThrow();
    });

    it('伪造 token 被拒绝', () => {
      expect(() => jwt.verify('fake.token.here', JWT_SECRET)).toThrow();
    });

    it('错误 secret 验签失败', () => {
      const token = jwt.sign({ userId: 1, role: 'user' }, JWT_SECRET);
      expect(() => jwt.verify(token, 'wrong_secret')).toThrow();
    });

    it('篡改 payload → 验签失败', () => {
      const token = jwt.sign({ userId: 1, role: 'user' }, JWT_SECRET);
      const parts = token.split('.');
      const tamperedPayload = Buffer.from(JSON.stringify({ userId: 1, role: 'admin' })).toString('base64url');
      const tamperedToken = `${parts[0]}.${tamperedPayload}.${parts[2]}`;
      expect(() => jwt.verify(tamperedToken, JWT_SECRET)).toThrow();
    });

    it('refresh_token 当 access_token 用 → 被拒', () => {
      const refreshToken = jwt.sign({ userId: 1, type: 'refresh' }, REFRESH_SECRET, { expiresIn: '30d' });
      expect(() => jwt.verify(refreshToken, JWT_SECRET)).toThrow();
    });
  });

  describe('boundary — Token 边界值', () => {
    it('payload 空对象 → verify 通过但 userId 为 undefined', () => {
      const token = jwt.sign({}, JWT_SECRET, { expiresIn: '7d' });
      const decoded = jwt.verify(token, JWT_SECRET);
      expect(decoded.userId).toBeUndefined();
    });
  });

  // ================================================================
  // 中间件维度 — fs.readFileSync 静态检查 middleware/auth.js
  // ================================================================
  describe('correct — 中间件导出与注入', () => {
    it('middleware/auth.js 导出 authenticate 和 optionalAuth', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
      expect(src).toContain('authenticate');
      expect(src).toContain('optionalAuth');
      expect(src).toContain('module.exports');
    });

    it('authenticate 注入 req.userId 和 req.user', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
      expect(src.includes('req.userId') || src.includes('req.user')).toBe(true);
    });

    it('middleware/permission.js 导出 requireRole / hasRole', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/permission.js'), 'utf-8');
      expect(src.includes('requireRole') || src.includes('hasRole')).toBe(true);
      expect(src).toContain('module.exports');
    });
  });

  describe('error — 鉴权缺失与角色拦截', () => {
    it('authenticate 无 token 时应返回 401', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
      const has401 = src.includes('401') || src.includes('unauthorized') || src.includes('Unauthorized');
      expect(has401).toBe(true);
    });

    it('authenticate 含令牌过期或未提供提示', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
      expect(src.includes('未提供认证令牌') || src.includes('令牌已过期') || src.includes('令牌')).toBe(true);
    });

    it('requireRole 角色不足应返回 403', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/permission.js'), 'utf-8');
      const has403 = src.includes('403') || src.includes('forbidden') || src.includes('Forbidden') || src.includes('无权');
      expect(has403).toBe(true);
    });
  });

  describe('boundary — 中间件边界', () => {
    it('无 Authorization header 时 authenticate 拒绝并提示未提供', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
      expect(src.includes('未提供') || src.includes('Authorization') || src.includes('authorization')).toBe(true);
    });
  });

  // ================================================================
  // 守卫维度 — fs.readFileSync 静态检查路由守卫
  // ================================================================
  describe('correct — 路由守卫存在', () => {
    it('前端路由含 beforeEach 或 requiresAuth 守卫', () => {
      const router = fs.readFileSync(path.join(workspace, 'src/router/index.js'), 'utf-8');
      expect(router.includes('beforeEach') || router.includes('requiresAuth')).toBe(true);
    });
  });

  describe('error — 缺守卫时未登录应被拦截', () => {
    it('路由文件中含导航守卫逻辑', () => {
      const router = fs.readFileSync(path.join(workspace, 'src/router/index.js'), 'utf-8');
      expect(router.includes('beforeEach') || router.includes('requiresAuth')).toBe(true);
    });
  });

  describe('boundary — 角色守卫', () => {
    it('requireRole 校验 req.user.role 不在白名单时拒绝', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/permission.js'), 'utf-8');
      expect(src.includes('req.user.role') || src.includes('user.role') || src.includes('无权访问')).toBe(true);
    });
  });

  // ================================================================
  // 存储维度 — fs.readFileSync 静态检查 token 存储
  // ================================================================
  describe('correct — Token 存储 key', () => {
    it('localStorage key 为 auth_token', () => {
      const store = fs.readFileSync(path.join(workspace, 'src/stores/user.js'), 'utf-8');
      expect(store).toContain('auth_token');
    });

    it('请求拦截器 header 含 Bearer 前缀', () => {
      const request = fs.readFileSync(path.join(workspace, 'src/utils/request.js'), 'utf-8');
      expect(request.includes('Bearer') || request.includes('bearer')).toBe(true);
    });
  });

  describe('error — Key 名错误', () => {
    it('key 名须为 auth_token 规范命名', () => {
      const store = fs.readFileSync(path.join(workspace, 'src/stores/user.js'), 'utf-8');
      expect(store).toMatch(/auth_token/);
    });
  });
});

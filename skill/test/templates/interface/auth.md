# auth 测试模板 — Token + 中间件 + 存储 + 守卫

🛑 绝对禁止 `require('../../app')` 和 `require('supertest')`

## 🛑 真理优先（最高优先级）

prompt 中 `## 🛑 下层真理` 包含上游已验证的 **中间件签名/注入字段/导出函数名**。

| `## 🛑 下层真理` 中的 `@truth t_infra_middleware` 块 | middleware 函数签名 + req 注入字段 | 🛑 JWT payload 字段名对齐真理 |
| testScenarios | input/output 描述 | 🟡 方向：测什么维度 |

🛑 **真理 > testScenarios 描述**。如果真理说中间件注入 `req.userId`(int)，测试就验证 `decoded.userId`。

## 按维度选择代码块

根据 testScenarios[].input 判断维度：
- 包含 `jwt.sign` / `jwt.verify` → 启用 **Token 维度**
- 包含 `fs.readFileSync middleware/auth.js` 或 `authenticate` → 启用 **中间件维度**
- 包含 `localStorage` / `auth_token` / `Bearer` → 启用 **存储维度**
- 包含 `router` / `requiresAuth` / `requiresAdmin` → 启用 **守卫维度**

🛑 四个维度按需组合——可能只用 1 个，也可能全部 4 个。

## Token 维度 — jwt.sign + jwt.verify 直调

```javascript
/** @jest-environment node */
const jwt = require('jsonwebtoken');
const JWT_SECRET = process.env.JWT_SECRET || 'test_jwt_secret';
const REFRESH_SECRET = process.env.JWT_REFRESH_SECRET || 'test_refresh_secret';

describe('{task_id}', () => {
  // ===== correct — 正常路径 =====
  describe('correct — Token 签名与验签', () => {
    it('jwt.sign 产出三段式 token', () => {
      const token = jwt.sign({ userId: 1, role: 'buyer' }, JWT_SECRET, { expiresIn: '7d' });
      const parts = token.split('.');
      expect(parts.length).toBe(3);
      parts.forEach(p => expect(() => Buffer.from(p, 'base64')).not.toThrow());
    });

    it('jwt.verify 解码出 userId 和 role', () => {
      const token = jwt.sign({ userId: 42, role: 'admin' }, JWT_SECRET);
      const decoded = jwt.verify(token, JWT_SECRET);
      expect(decoded.userId).toBe(42);
      expect(decoded.role).toBe('admin');
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

  // ===== error — 异常拒绝 =====
  describe('error — Token 拒绝', () => {
    it('过期 token 被拒绝', () => {
      const token = jwt.sign({ userId: 1 }, JWT_SECRET, { expiresIn: '0s' });
      expect(() => jwt.verify(token, JWT_SECRET)).toThrow();
    });

    it('伪造 token 被拒绝', () => {
      expect(() => jwt.verify('fake.token.here', JWT_SECRET)).toThrow();
    });

    it('错误 secret 被拒绝', () => {
      const token = jwt.sign({ userId: 1 }, JWT_SECRET);
      expect(() => jwt.verify(token, 'wrong_secret')).toThrow();
    });

    it('篡改 payload → 验签失败', () => {
      const token = jwt.sign({ userId: 1, role: 'buyer' }, JWT_SECRET);
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

  // ===== boundary — 边界 =====
  describe('boundary — 边界值', () => {
    it('payload 空对象 → verify 通过但 userId 为 undefined', () => {
      const token = jwt.sign({}, JWT_SECRET, { expiresIn: '7d' });
      const decoded = jwt.verify(token, JWT_SECRET);
      expect(decoded.userId).toBeUndefined();
    });
  });
});
```

## 中间件维度 — 静态文件检查

```javascript
/** @jest-environment node */
const fs = require('fs');
const path = require('path');
const workspace = path.resolve(__dirname, '..');  // 🛑 铁律：test/ 往上一级即项目根，禁止写 '../..' 或其他层级！

describe('{task_id} — middleware', () => {
  describe('correct — 中间件导出与注入', () => {
    it('authenticate 注入 req.userId', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
      expect(src.includes('req.userId') || src.includes('req.user')).toBe(true);
    });

    it('导出 authenticate 和 optionalAuth', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
      expect(src).toContain('authenticate');
      expect(src).toContain('optionalAuth');
      expect(src).toContain('module.exports');
    });
  });

  describe('error — 鉴权缺失', () => {
    it('无 token 时应返回 401', () => {
      const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
      const has401 = src.includes('401') || src.includes('unauthorized') || src.includes('Unauthorized');
      expect(has401).toBe(true);
    });
  });
});
```

## 存储维度 — 静态文件检查

```javascript
describe('{task_id} — storage', () => {
  describe('correct — Token 存储 key', () => {
    it('localStorage key 为 auth_token', () => {
      const store = fs.readFileSync(path.join(workspace, 'src/stores/user.js'), 'utf-8');
      expect(store).toContain('auth_token');
    });

    it('header 含 Bearer 前缀', () => {
      const request = fs.readFileSync(path.join(workspace, 'src/utils/request.js'), 'utf-8');
      expect(request.includes('Bearer') || request.includes('bearer')).toBe(true);
    });
  });

  describe('error — Key 名错误', () => {
    it('key 名不是 auth_token → 取不到 token', () => {
      const store = fs.readFileSync(path.join(workspace, 'src/stores/user.js'), 'utf-8');
      expect(store).toMatch(/auth_token/);
    });
  });
});
```

## 守卫维度 — 静态文件检查

```javascript
describe('{task_id} — guard', () => {
  describe('correct — 路由守卫存在', () => {
    it('requiresAuth 路由守卫存在', () => {
      const router = fs.readFileSync(path.join(workspace, 'src/router/index.js'), 'utf-8');
      expect(router).toContain('requiresAuth');
    });

    it('requiresMerchant 或 requiresAdmin 守卫存在', () => {
      const router = fs.readFileSync(path.join(workspace, 'src/router/index.js'), 'utf-8');
      expect(router.includes('requiresMerchant') || router.includes('requiresAdmin')).toBe(true);
    });
  });

  describe('error — 缺守卫', () => {
    it('无守卫时未登录应被拦截', () => {
      const router = fs.readFileSync(path.join(workspace, 'src/router/index.js'), 'utf-8');
      expect(router.includes('beforeEach') || router.includes('requiresAuth')).toBe(true);
    });
  });
});
```

🛑 四个维度按 prompt 中 testScenarios 的 category 选择对应 describe 块
🛑 token 维度禁止 require('../../app') 和 supertest
🛑 mw/store/guard 维度用 fs.readFileSync + toContain/toMatch

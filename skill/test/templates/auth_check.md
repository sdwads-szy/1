# Auth 检查模板 (Layer 2: auth)

## 混合层: Token链走HTTP, middleware/frontend走静态

```javascript
const request = require('supertest');
const app = require('../../app');
const fs = require('fs');
const path = require('path');
const jwt = require('jsonwebtoken');

const workspace = process.env.WORKSPACE || '../../';
const JWT_SECRET = process.env.JWT_SECRET || 'dev_jwt_secret';

describe('{task_id}', () => {
  // A2.1: Token签发链 (HTTP)
  it('注册后 token 可被 jwt.verify 验证', async () => {
    const phone = `test_${Date.now()}@test.com`;
    const password = 'Test123456';
    const regRes = await request(app)
      .post('/api/auth/register')
      .send({ phone, password, smsCode: '000000' });  // 测试环境mock验证码
    expect(regRes.body.success).toBe(true);
    const token = regRes.body.data.token;
    const decoded = jwt.verify(token, JWT_SECRET);
    expect(decoded.userId).toBeGreaterThan(0);
    expect(decoded.role).toBeTruthy();
  });

  // A2.2: Token刷新链 (HTTP)
  it('刷新后旧token返回401, 新token有效', async () => {
    const phone = `refresh_${Date.now()}@test.com`;
    await request(app).post('/api/auth/register').send({ phone, password: 'Test123456', smsCode: '000000' });
    const loginRes = await request(app).post('/api/auth/login').send({ phone, password: 'Test123456' });
    const oldToken = loginRes.body.data.token;
    const refreshToken = loginRes.body.data.refreshToken;

    const refreshRes = await request(app).post('/api/auth/refresh').send({ refreshToken });
    expect(refreshRes.body.success).toBe(true);
    const newToken = refreshRes.body.data.token;

    // 旧token被拉黑
    const profileRes = await request(app).get('/api/user/profile').set('Authorization', `Bearer ${oldToken}`);
    expect(profileRes.status).toBe(401);

    // 新token有效
    const profileRes2 = await request(app).get('/api/user/profile').set('Authorization', `Bearer ${newToken}`);
    expect(profileRes2.body.success).toBe(true);
  });

  // A2.3: Middleware 注入 (静态)
  it('auth middleware 设置 req.userId', () => {
    const src = fs.readFileSync(path.join(workspace, 'middleware/auth.js'), 'utf-8');
    expect(src).toMatch(/req\.userId\s*=\s*decoded\.userId/);
  });

  // A2.4: 前端 Token 存储 (静态)
  it('前端 localStorage key 为 auth_token', () => {
    const store = fs.readFileSync(path.join(workspace, 'src/stores/user.js'), 'utf-8');
    expect(store).toContain('auth_token');
    expect(store).not.toContain("'token'"); // 不能只用 'token' 作为key
  });

  // A2.5: 路由守卫 (静态)
  it('路由守卫检查 requiresAuth 和 requiresAdmin', () => {
    const router = fs.readFileSync(path.join(workspace, 'src/router/index.js'), 'utf-8');
    expect(router).toContain('requiresAuth');
    expect(router).toContain('requiresAdmin');
  });
});
```

## 关键规则
1. 混合层: Token签发和刷新需要真实HTTP调用 (supertest)
2. middleware注入和前端存储走静态文件检查
3. 测试环境mock短信验证码 (smsCode='000000')
4. 每个 auth 子层对应至少 1 个 `it()` 块

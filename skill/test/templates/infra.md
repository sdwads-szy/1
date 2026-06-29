# infra 层测试模板 — jest (CJS)

**适用**: config/ utils/ .env 校验
**框架**: Jest (CJS) — `require` + `jest.mock`
**特点**: mock 外部 npm 包，验证本地模块导出、环境变量、连接可用性

## 模板

```js
// ── mock 外部依赖 ──
jest.mock('winston', () => ({
  createLogger: jest.fn(() => ({ info: jest.fn(), error: jest.fn() })),
  format: { combine: jest.fn(), timestamp: jest.fn(), json: jest.fn() },
  transports: { Console: jest.fn(), File: jest.fn() }
}));
jest.mock('mysql2/promise', () => ({
  createPool: jest.fn(() => ({ getConnection: jest.fn(), execute: jest.fn() }))
}));
jest.mock('ioredis', () => jest.fn(() => ({ ping: jest.fn(), get: jest.fn(), set: jest.fn(), quit: jest.fn() })));
jest.mock('jsonwebtoken', () => ({ sign: jest.fn(), verify: jest.fn() }));
jest.mock('bcryptjs', () => ({ hash: jest.fn(), compare: jest.fn() }));

// ── config/db.js ──
describe('config/db.js', () => {
  beforeEach(() => { jest.clearAllMocks(); });

  it('导出 pool, query, beginTransaction, commit, rollback, testConnection', () => {
    const db = require('../../config/db');
    expect(db.pool).toBeDefined();
    expect(typeof db.query).toBe('function');
    expect(typeof db.beginTransaction).toBe('function');
    expect(typeof db.commit).toBe('function');
    expect(typeof db.rollback).toBe('function');
    expect(typeof db.testConnection).toBe('function');
  });
});

// ── utils/response.js ──
describe('utils/response.js', () => {
  let res;
  beforeEach(() => { res = { json: jest.fn(), status: jest.fn(() => res) }; });

  it('success → {success:true, code:200, message, data}', () => {
    require('../../utils/response').success(res, 'ok', { id: 1 });
    expect(res.json).toHaveBeenCalledWith({ success: true, code: 200, message: 'ok', data: { id: 1 } });
  });

  it('fail → {success:false, code, message}', () => {
    require('../../utils/response').fail(res, '库存不足', 422);
    expect(res.status).toHaveBeenCalledWith(422);
    expect(res.json).toHaveBeenCalledWith(expect.objectContaining({ success: false, code: 422 }));
  });

  it('unauthorized → 401', () => {
    require('../../utils/response').unauthorized(res);
    expect(res.status).toHaveBeenCalledWith(401);
  });
});

// ── utils/encryption.js ──
describe('utils/encryption.js', () => {
  it('encrypt + decrypt round-trip', () => {
    const { encrypt, decrypt } = require('../../utils/encryption');
    const cipher = encrypt('13800138000');
    expect(cipher).not.toBe('13800138000');
    expect(decrypt(cipher)).toBe('13800138000');
  });

  it('encrypt 两次结果不同（随机IV）', () => {
    const { encrypt } = require('../../utils/encryption');
    const c1 = encrypt('13800138000');
    const c2 = encrypt('13800138000');
    expect(c1).not.toBe(c2);
  });
});

// ── .env 校验 ──
describe('.env', () => {
  it('四件套变量集一致', () => {
    const fs = require('fs');
    const parseEnv = (f) => Object.keys(require('dotenv').parse(fs.readFileSync(f)));
    const keys = ['.env', '.env.example', '.env.development', '.env.production'].map(f => {
      try { return parseEnv(`../../${f}`); } catch { return []; }
    });
    const exampleKeys = keys[1]; // .env.example 为基准
    keys.forEach((k, i) => {
      const missing = exampleKeys.filter(kk => !k.includes(kk));
      if (missing.length) fail(`文件${i} 缺少变量: ${missing.join(', ')}`);
    });
  });

  it('必填变量非占位符', () => {
    require('dotenv').config();
    expect(process.env.DB_HOST).toBeTruthy();
    expect(process.env.DB_HOST).not.toMatch(/your_.*_here/);
    expect(process.env.ENCRYPTION_KEY).toHaveLength(64);
  });
});

// ── middleware 管道 ──
describe('middleware', () => {
  it('CORS 允许配置来源', () => {
    const cors = require('cors');
    const mw = cors({ origin: '*' });
    const req = { method: 'OPTIONS', headers: { origin: 'https://example.com' } };
    const res = { setHeader: jest.fn(), end: jest.fn() };
    mw(req, res, () => {});
    expect(res.setHeader).toHaveBeenCalledWith('Access-Control-Allow-Origin', expect.any(String));
  });

  it('JSON body 解析 → req.body', () => {
    const express = require('express');
    const app = express();
    app.use(express.json());
    // 验证中间件链不抛异常
  });

  it('404 → 返回 code/message', async () => {
    const request = require('supertest');
    const app = require('../../app');
    const res = await request(app).get('/nonexistent-path-xyz');
    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty('code');
  });
});
```

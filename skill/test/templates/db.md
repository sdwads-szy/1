# db 层测试模板 — jest (CJS)

**适用**: DDL 验证（表结构/字段/约束/索引/FK）
**框架**: Jest (CJS) — 直连真实 MySQL，不 mock 数据库
**前置**: `scripts/init-db.js` 已执行

## 模板

```js
const mysql = require('mysql2/promise');

let conn;
beforeAll(async () => {
  conn = await mysql.createConnection({
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 3306,
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'testdb'
  });
});
afterAll(async () => { await conn.end(); });

// ── 表存在 ──
describe('users 表', () => {
  it('表存在', async () => {
    const [rows] = await conn.execute(
      "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=? AND TABLE_NAME='users'",
      [process.env.DB_NAME || 'testdb']
    );
    expect(rows.length).toBe(1);
  });

  // ── 字段类型 ──
  it('字段类型与 model 契约一致', async () => {
    const [cols] = await conn.execute('DESCRIBE users');
    const map = {};
    cols.forEach(c => { map[c.Field] = { type: c.Type, null: c.Null, key: c.Key, default: c.Default }; });

    expect(map.id).toMatchObject({ type: expect.stringContaining('int'), key: 'PRI' });
    expect(map.phone).toMatchObject({ type: 'varchar(128)', null: 'NO', key: 'UNI' });
    expect(map.role).toMatchObject({ type: expect.stringContaining('enum'), null: 'NO', default: 'buyer' });
    expect(map.status).toMatchObject({ type: expect.stringContaining('enum'), null: 'NO', default: 'active' });
    expect(map.created_at).toMatchObject({ type: expect.stringContaining('timestamp'), null: 'NO' });
  });

  // ── UNIQUE ──
  it('phone UNIQUE 约束', async () => {
    await conn.execute("INSERT INTO users (phone,password_hash,role) VALUES ('13800000001','h1','buyer')");
    await expect(
      conn.execute("INSERT INTO users (phone,password_hash,role) VALUES ('13800000001','h2','buyer')")
    ).rejects.toThrow();
    await conn.execute("DELETE FROM users WHERE phone='13800000001'");
  });

  // ── ENUM ──
  it('role ENUM 值域限制', async () => {
    await expect(
      conn.execute("INSERT INTO users (phone,password_hash,role) VALUES ('13800000099','h','superadmin')")
    ).rejects.toThrow();
  });

  // ── INDEX ──
  it('索引 idx_role_status 存在', async () => {
    const [idx] = await conn.execute("SHOW INDEX FROM users WHERE Key_name='idx_role_status'");
    expect(idx.length).toBeGreaterThan(0);
  });
});

// ── FK 约束 ──
describe('addresses 表', () => {
  it('表存在 + 字段类型正确', async () => {
    const [rows] = await conn.execute(
      "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=? AND TABLE_NAME='addresses'",
      [process.env.DB_NAME || 'testdb']
    );
    expect(rows.length).toBe(1);

    const [cols] = await conn.execute('DESCRIBE addresses');
    const map = {};
    cols.forEach(c => { map[c.Field] = c.Type; });
    expect(map.user_id).toMatch(/int/);
    expect(map.province).toMatch(/varchar/);
    expect(map.detail).toMatch(/varchar/);
  });

  it('FK user_id → users(id)', async () => {
    await expect(
      conn.execute("INSERT INTO addresses (user_id,province,city,district,detail,phone,name) VALUES (99999,'浙','杭','西','x','138','张')")
    ).rejects.toThrow(); // ER_NO_REFERENCED_ROW_2
  });
});
```

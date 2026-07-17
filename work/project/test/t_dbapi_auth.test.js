/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_auth', () => {
  let conn;
  beforeAll(async () => {
    conn = await mysql.createConnection({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '3306'),
      user: process.env.DB_USER || 'root',
      password: process.env.DB_PASSWORD || '',
      database: process.env.DB_NAME || 'testdb',
    });
  });
  afterAll(async () => { if (conn) await conn.end(); });

  // ══ correct: users 表列名存在（authService.findUserByMobile / findUserById / createUser）══
  describe('correct — users 表列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `users`');
      columns = rows.map(r => r.Field);
    });

    // 真理 DDL 中 users 表全部列名
    const expectedUsersCols = ['id', 'mobile', 'password_hash', 'nickname', 'avatar', 'role', 'status', 'created_at', 'updated_at'];
    it.each(expectedUsersCols)('列 %s 在 users 表中存在', (col) => {
      expect(columns).toContain(col);
    });
  });

  // ══ correct: refresh_tokens 表列名存在（authService.createRefreshToken / findTokenByHash / deleteToken）══
  describe('correct — refresh_tokens 表列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refresh_tokens`');
      columns = rows.map(r => r.Field);
    });

    // 真理 DDL 中 refresh_tokens 表全部列名
    const expectedRtCols = ['id', 'user_id', 'token_hash', 'expires_at', 'created_at'];
    it.each(expectedRtCols)('列 %s 在 refresh_tokens 表中存在', (col) => {
      expect(columns).toContain(col);
    });
  });

  // ══ boundary: users 表约束 — NOT NULL / PK / AUTO_INCREMENT / ENUM ══
  describe('boundary — users 表约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `users`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('mobile 为 NOT NULL', () => {
      expect(colMap['mobile'].Null).toBe('NO');
    });

    it('password_hash 为 NOT NULL', () => {
      expect(colMap['password_hash'].Null).toBe('NO');
    });

    it('nickname 为 NOT NULL', () => {
      expect(colMap['nickname'].Null).toBe('NO');
    });

    it('role 为 NOT NULL', () => {
      expect(colMap['role'].Null).toBe('NO');
    });

    it('status 为 NOT NULL', () => {
      expect(colMap['status'].Null).toBe('NO');
    });

    it('role ENUM 值正确', () => {
      expect(colMap['role'].Type).toContain('enum');
      expect(colMap['role'].Type).toContain('user');
      expect(colMap['role'].Type).toContain('merchant');
      expect(colMap['role'].Type).toContain('admin');
    });

    it("role DEFAULT 'user'", () => {
      expect(colMap['role'].Default).toBe('user');
    });

    it('status ENUM 值正确', () => {
      expect(colMap['status'].Type).toContain('enum');
      expect(colMap['status'].Type).toContain('active');
      expect(colMap['status'].Type).toContain('disabled');
    });

    it("status DEFAULT 'active'", () => {
      expect(colMap['status'].Default).toBe('active');
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });
  });

  // ══ boundary: refresh_tokens 表约束 — NOT NULL / PK / AUTO_INCREMENT ══
  describe('boundary — refresh_tokens 表约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refresh_tokens`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('user_id 为 NOT NULL', () => {
      expect(colMap['user_id'].Null).toBe('NO');
    });

    it('token_hash 为 NOT NULL', () => {
      expect(colMap['token_hash'].Null).toBe('NO');
    });

    it('expires_at 为 NOT NULL', () => {
      expect(colMap['expires_at'].Null).toBe('NO');
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });
  });

  // ══ boundary: users 表级约束 — UNIQUE mobile ══
  describe('boundary — users 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `users`');
      createTable = rows[0]['Create Table'];
    });

    it('UNIQUE 约束 mobile', () => {
      expect(createTable).toContain('UNIQUE');
    });
  });

  // ══ boundary: refresh_tokens 表级约束 — UNIQUE token_hash + FK user_id ══
  describe('boundary — refresh_tokens 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `refresh_tokens`');
      createTable = rows[0]['Create Table'];
    });

    it('UNIQUE 约束 token_hash', () => {
      expect(createTable).toContain('UNIQUE');
    });

    it('FK 约束存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ error: 列名缺失 — 编造列名不在 DDL 中 ══
  describe('error — 列名缺失', () => {
    let usersColumns, rtColumns;
    beforeAll(async () => {
      const [uRows] = await conn.query('SHOW COLUMNS FROM `users`');
      usersColumns = uRows.map(r => r.Field);
      const [rRows] = await conn.query('SHOW COLUMNS FROM `refresh_tokens`');
      rtColumns = rRows.map(r => r.Field);
    });

    it("'username' 不在 users DDL 中（DDL 使用 nickname）", () => {
      expect(usersColumns).not.toContain('username');
    });

    it("'token' 不在 refresh_tokens DDL 中（DDL 使用 token_hash）", () => {
      expect(rtColumns).not.toContain('token');
    });

    it('编造列名 xyz_not_a_column 不在任何表中', () => {
      expect(usersColumns).not.toContain('xyz_not_a_column');
      expect(rtColumns).not.toContain('xyz_not_a_column');
    });
  });
});

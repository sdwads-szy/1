/** @jest-environment node */
require('dotenv').config();
const mysql = require('mysql2/promise');

describe('t_dbapi_user', () => {
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

  // ══ correct: user_addresses 列名存在（SHOW COLUMNS 查真实数据库） ══
  describe('correct — user_addresses 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `user_addresses`');
      columns = rows.map(r => r.Field);
    });

    // INSERT 列 (userService.createAddress)
    it('INSERT 列 user_id 在表中存在', () => { expect(columns).toContain('user_id'); });
    it('INSERT 列 province 在表中存在', () => { expect(columns).toContain('province'); });
    it('INSERT 列 city 在表中存在', () => { expect(columns).toContain('city'); });
    it('INSERT 列 district 在表中存在', () => { expect(columns).toContain('district'); });
    it('INSERT 列 detail 在表中存在', () => { expect(columns).toContain('detail'); });
    it('INSERT 列 phone 在表中存在', () => { expect(columns).toContain('phone'); });
    it('INSERT 列 contact_name 在表中存在', () => { expect(columns).toContain('contact_name'); });
    it('INSERT 列 is_default 在表中存在', () => { expect(columns).toContain('is_default'); });

    // SELECT 列 (userService.getAddressesByUser)
    it('SELECT 列 id 在表中存在', () => { expect(columns).toContain('id'); });
    it('SELECT 列 created_at 在表中存在', () => { expect(columns).toContain('created_at'); });

    // UPDATE 列 (userService.updateAddress) — province/city/district/detail/phone/contact_name/is_default 已在 INSERT 覆盖
    // DELETE 列 (userService.deleteAddress) — id + user_id 已在上面覆盖
  });

  // ══ boundary: NOT NULL / PK / AUTO_INCREMENT / FK / DEFAULT ══
  describe('boundary — user_addresses 约束', () => {
    let colMap;
    let createTable;
    beforeAll(async () => {
      const [colRows] = await conn.query('SHOW COLUMNS FROM `user_addresses`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });

      const [ctRows] = await conn.query('SHOW CREATE TABLE `user_addresses`');
      createTable = ctRows[0]['Create Table'];
    });

    // NOT NULL 约束
    it('user_id 为 NOT NULL', () => { expect(colMap['user_id'].Null).toBe('NO'); });
    it('province 为 NOT NULL', () => { expect(colMap['province'].Null).toBe('NO'); });
    it('city 为 NOT NULL', () => { expect(colMap['city'].Null).toBe('NO'); });
    it('district 为 NOT NULL', () => { expect(colMap['district'].Null).toBe('NO'); });
    it('detail 为 NOT NULL', () => { expect(colMap['detail'].Null).toBe('NO'); });
    it('phone 为 NOT NULL', () => { expect(colMap['phone'].Null).toBe('NO'); });
    it('contact_name 为 NOT NULL', () => { expect(colMap['contact_name'].Null).toBe('NO'); });
    it('is_default 为 NOT NULL', () => { expect(colMap['is_default'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    // PRIMARY KEY
    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });

    // AUTO_INCREMENT
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });

    // FOREIGN KEY — user_id → users.id
    it('FOREIGN KEY user_id 约束存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });

    // DEFAULT 值
    it('is_default DEFAULT 0', () => { expect(colMap['is_default'].Default).toBe('0'); });
  });

  // ══ error: 列名缺失 ══
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `user_addresses`');
      columns = rows.map(r => r.Field);
    });

    it('receiver_name 不在 user_addresses 表中（DDL 使用 contact_name）', () => {
      expect(columns).not.toContain('receiver_name');
    });

    it('不存在的列名 not.toContain', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });
});

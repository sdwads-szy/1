/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_reconciliation', () => {
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

  // ══ correct: INSERT INTO reconciliation_statements — 列名对齐 ══
  describe('correct — reconciliation_statements INSERT 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `reconciliation_statements`');
      columns = rows.map(r => r.Field);
    });

    it('merchant_id 在 reconciliation_statements DDL 中存在', () => {
      expect(columns).toContain('merchant_id');
    });
    it('date 在 reconciliation_statements DDL 中存在', () => {
      expect(columns).toContain('date');
    });
    it('diff 在 reconciliation_statements DDL 中存在', () => {
      expect(columns).toContain('diff');
    });
    it('status 在 reconciliation_statements DDL 中存在', () => {
      expect(columns).toContain('status');
    });
    it('note 在 reconciliation_statements DDL 中存在', () => {
      expect(columns).toContain('note');
    });
  });

  // ══ error: 编造列名 — 'difference' 不在 DDL 中（正确列名是 diff） ══
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `reconciliation_statements`');
      columns = rows.map(r => r.Field);
    });

    it('difference 不在 reconciliation_statements DDL 字段列表中（DDL 使用 diff）', () => {
      expect(columns).not.toContain('difference');
    });

    it('不存在的列名 xyz_not_a_column 也不应出现', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══ boundary: NOT NULL / PK / AUTO_INCREMENT 约束 ══
  describe('boundary — reconciliation_statements NOT NULL / PK / AUTO_INCREMENT', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `reconciliation_statements`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => {
      expect(colMap['id'].Null).toBe('NO');
    });
    it('merchant_id 为 NOT NULL', () => {
      expect(colMap['merchant_id'].Null).toBe('NO');
    });
    it('date 为 NOT NULL', () => {
      expect(colMap['date'].Null).toBe('NO');
    });
    it('diff 为 NOT NULL', () => {
      expect(colMap['diff'].Null).toBe('NO');
    });
    it('status 为 NOT NULL', () => {
      expect(colMap['status'].Null).toBe('NO');
    });
    it('note 可为 NULL', () => {
      expect(colMap['note'].Null).toBe('YES');
    });
    it('created_at 为 NOT NULL', () => {
      expect(colMap['created_at'].Null).toBe('NO');
    });
    it('updated_at 为 NOT NULL', () => {
      expect(colMap['updated_at'].Null).toBe('NO');
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });
  });

  // ══ boundary: UNIQUE(merchant_id,date) + ENUM + FK + DEFAULT ══
  describe('boundary — reconciliation_statements 表级约束', () => {
    let createTable;
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `reconciliation_statements`');
      createTable = rows[0]['Create Table'];
      const [colRows] = await conn.query('SHOW COLUMNS FROM `reconciliation_statements`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });
    });

    it('UNIQUE KEY (merchant_id, date) 存在', () => {
      expect(createTable).toContain('UNIQUE');
      expect(createTable).toContain('merchant_id');
      expect(createTable).toContain('date');
    });

    it('status ENUM 值正确 — pending, resolved, ignored', () => {
      expect(colMap['status'].Type).toContain('enum');
      expect(colMap['status'].Type).toContain('pending');
      expect(colMap['status'].Type).toContain('resolved');
      expect(colMap['status'].Type).toContain('ignored');
    });

    it('status DEFAULT pending', () => {
      expect(colMap['status'].Default).toBe('pending');
    });

    it('diff DECIMAL(10,2) DEFAULT 0.00', () => {
      expect(colMap['diff'].Default).toBe('0.00');
    });

    it('FOREIGN KEY merchant_id → merchants.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
      expect(createTable).toContain('merchant_id');
    });
  });

  // ══ boundary: idx_status 索引 ══
  describe('boundary — reconciliation_statements 索引', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `reconciliation_statements`');
      createTable = rows[0]['Create Table'];
    });

    it('idx_status 索引存在', () => {
      expect(createTable).toContain('idx_status');
    });

    it('idx_merchant_date UNIQUE 索引存在', () => {
      expect(createTable).toContain('idx_merchant_date');
    });
  });
});

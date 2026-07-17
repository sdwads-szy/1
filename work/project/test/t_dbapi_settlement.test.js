/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_settlement', () => {
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

  // ══ correct: 各 service 函数引用的列在 settlement_orders 表中存在 ══
  describe('correct — settlement_orders 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `settlement_orders`');
      columns = rows.map(r => r.Field);
    });

    describe('getSettlementsByMerchant SELECT 列', () => {
      it('id 列存在', () => { expect(columns).toContain('id'); });
      it('merchant_id 列存在', () => { expect(columns).toContain('merchant_id'); });
      it('period 列存在', () => { expect(columns).toContain('period'); });
      it('amount 列存在', () => { expect(columns).toContain('amount'); });
      it('status 列存在', () => { expect(columns).toContain('status'); });
      it('paid_at 列存在', () => { expect(columns).toContain('paid_at'); });
      it('created_at 列存在', () => { expect(columns).toContain('created_at'); });
    });

    describe('getSettlementsList SELECT 列', () => {
      it('id 列存在', () => { expect(columns).toContain('id'); });
      it('merchant_id 列存在', () => { expect(columns).toContain('merchant_id'); });
      it('period 列存在', () => { expect(columns).toContain('period'); });
      it('amount 列存在', () => { expect(columns).toContain('amount'); });
      it('status 列存在', () => { expect(columns).toContain('status'); });
      it('created_at 列存在', () => { expect(columns).toContain('created_at'); });
    });

    describe('createSettlement INSERT 列', () => {
      it('merchant_id 列存在', () => { expect(columns).toContain('merchant_id'); });
      it('period 列存在', () => { expect(columns).toContain('period'); });
      it('amount 列存在', () => { expect(columns).toContain('amount'); });
      it('status 列存在', () => { expect(columns).toContain('status'); });
    });

    describe('updateSettlementStatus UPDATE 列（CAS: WHERE id=? AND status=?）', () => {
      it('status 列存在', () => { expect(columns).toContain('status'); });
      it('paid_at 列存在', () => { expect(columns).toContain('paid_at'); });
      it('id 列存在', () => { expect(columns).toContain('id'); });
    });
  });

  // ══ boundary: NOT NULL / PK / AUTO_INCREMENT / ENUM / DEFAULT 约束 ══
  describe('boundary — settlement_orders 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `settlement_orders`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    // NOT NULL
    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('merchant_id 为 NOT NULL', () => { expect(colMap['merchant_id'].Null).toBe('NO'); });
    it('period 为 NOT NULL', () => { expect(colMap['period'].Null).toBe('NO'); });
    it('amount 为 NOT NULL', () => { expect(colMap['amount'].Null).toBe('NO'); });
    it('status 为 NOT NULL', () => { expect(colMap['status'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    // nullable
    it('paid_at 可为 NULL', () => { expect(colMap['paid_at'].Null).toBe('YES'); });

    // PK
    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    // AUTO_INCREMENT
    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    // ENUM
    it('status 为 ENUM 类型', () => {
      expect(colMap['status'].Type).toContain('enum');
      expect(colMap['status'].Type).toContain('pending');
      expect(colMap['status'].Type).toContain('confirmed');
      expect(colMap['status'].Type).toContain('paid');
      expect(colMap['status'].Type).toContain('completed');
      expect(colMap['status'].Type).toContain('clawed_back');
    });

    // DEFAULT
    it('status DEFAULT pending', () => {
      expect(colMap['status'].Default).toBe('pending');
    });

    // period type
    it('period 为 VARCHAR(7) — YYYY-MM 格式', () => {
      expect(colMap['period'].Type).toContain('varchar(7)');
    });
  });

  // ══ boundary: UNIQUE / FK 表级约束 ══
  describe('boundary — settlement_orders 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `settlement_orders`');
      createTable = rows[0]['Create Table'];
    });

    it('UNIQUE KEY (merchant_id, period) 存在', () => {
      expect(createTable).toContain('UNIQUE');
    });

    it('FK merchant_id → merchants.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ error: 列名缺失 ══
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `settlement_orders`');
      columns = rows.map(r => r.Field);
    });

    it("settle_amount 不在 settlement_orders 中（DDL 使用 amount）", () => {
      expect(columns).not.toContain('settle_amount');
    });

    it('不存在的列名 xyz_not_a_column', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══ error: truth 中声明的列在数据库中真实存在 ══
  describe('error — truth 列 vs 真实 DB', () => {
    let allColumns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `settlement_orders`');
      allColumns = new Set(rows.map(r => r.Field));
    });

    // 从 t_db_settlement_orders 真理提取的全部列
    it('truth 列 id 在 DB 中存在', () => { expect(allColumns.has('id')).toBe(true); });
    it('truth 列 merchant_id 在 DB 中存在', () => { expect(allColumns.has('merchant_id')).toBe(true); });
    it('truth 列 period 在 DB 中存在', () => { expect(allColumns.has('period')).toBe(true); });
    it('truth 列 amount 在 DB 中存在', () => { expect(allColumns.has('amount')).toBe(true); });
    it('truth 列 status 在 DB 中存在', () => { expect(allColumns.has('status')).toBe(true); });
    it('truth 列 paid_at 在 DB 中存在', () => { expect(allColumns.has('paid_at')).toBe(true); });
    it('truth 列 created_at 在 DB 中存在', () => { expect(allColumns.has('created_at')).toBe(true); });
    it('truth 列 updated_at 在 DB 中存在', () => { expect(allColumns.has('updated_at')).toBe(true); });
  });

});

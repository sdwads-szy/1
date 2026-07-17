/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_inventory', () => {
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

  // ══ correct: inventories 列名存在（SHOW COLUMNS 查真实数据库）══
  describe('correct — inventories 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `inventories`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 inventories 表中存在', () => {
      expect(columns).toContain('id');
    });
    it('列 sku_id 在 inventories 表中存在', () => {
      expect(columns).toContain('sku_id');
    });
    it('列 shop_id 在 inventories 表中存在', () => {
      expect(columns).toContain('shop_id');
    });
    it('列 stock 在 inventories 表中存在', () => {
      expect(columns).toContain('stock');
    });
    it('列 frozen_stock 在 inventories 表中存在', () => {
      expect(columns).toContain('frozen_stock');
    });
    it('列 version 在 inventories 表中存在', () => {
      expect(columns).toContain('version');
    });
    it('列 created_at 在 inventories 表中存在', () => {
      expect(columns).toContain('created_at');
    });
    it('列 updated_at 在 inventories 表中存在', () => {
      expect(columns).toContain('updated_at');
    });
  });

  // ══ boundary: NOT NULL / PK / AUTO_INCREMENT 约束 ══
  describe('boundary — inventories 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `inventories`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => {
      expect(colMap['id'].Null).toBe('NO');
    });
    it('sku_id 为 NOT NULL', () => {
      expect(colMap['sku_id'].Null).toBe('NO');
    });
    it('shop_id 为 NOT NULL', () => {
      expect(colMap['shop_id'].Null).toBe('NO');
    });
    it('stock 为 NOT NULL', () => {
      expect(colMap['stock'].Null).toBe('NO');
    });
    it('frozen_stock 为 NOT NULL', () => {
      expect(colMap['frozen_stock'].Null).toBe('NO');
    });
    it('version 为 NOT NULL', () => {
      expect(colMap['version'].Null).toBe('NO');
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

    it('stock DEFAULT 0', () => {
      expect(colMap['stock'].Default).toBe('0');
    });

    it('frozen_stock DEFAULT 0', () => {
      expect(colMap['frozen_stock'].Default).toBe('0');
    });

    it('version DEFAULT 0', () => {
      expect(colMap['version'].Default).toBe('0');
    });
  });

  // ══ boundary: UNIQUE / FOREIGN KEY 表级约束 ══
  describe('boundary — inventories 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `inventories`');
      createTable = rows[0]['Create Table'];
    });

    it('UNIQUE KEY (sku_id, shop_id) 存在', () => {
      expect(createTable).toContain('UNIQUE');
    });

    it('FOREIGN KEY 约束存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ error: 编造列名不存在 ══
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `inventories`');
      columns = rows.map(r => r.Field);
    });

    it("编造列名 'quantity' 不在 inventories 表中", () => {
      expect(columns).not.toContain('quantity');
    });
  });

  // ══ error: truth 中声明的列在真实 DB 中全部存在 ══
  describe('error — truth 列 vs 真实 DB', () => {
    let allColumns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `inventories`');
      allColumns = new Set(rows.map(r => r.Field));
    });

    it('truth 列 id 在 DB 中存在', () => {
      expect(allColumns.has('id')).toBe(true);
    });
    it('truth 列 sku_id 在 DB 中存在', () => {
      expect(allColumns.has('sku_id')).toBe(true);
    });
    it('truth 列 shop_id 在 DB 中存在', () => {
      expect(allColumns.has('shop_id')).toBe(true);
    });
    it('truth 列 stock 在 DB 中存在', () => {
      expect(allColumns.has('stock')).toBe(true);
    });
    it('truth 列 frozen_stock 在 DB 中存在', () => {
      expect(allColumns.has('frozen_stock')).toBe(true);
    });
    it('truth 列 version 在 DB 中存在', () => {
      expect(allColumns.has('version')).toBe(true);
    });
    it('truth 列 created_at 在 DB 中存在', () => {
      expect(allColumns.has('created_at')).toBe(true);
    });
    it('truth 列 updated_at 在 DB 中存在', () => {
      expect(allColumns.has('updated_at')).toBe(true);
    });
  });

});

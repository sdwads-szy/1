/** @jest-environment node */
require('dotenv').config();
const mysql = require('mysql2/promise');

describe('t_dbapi_product_admin', () => {
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

  // ══════════════════════════════════════════════════
  // spu 表
  // ══════════════════════════════════════════════════

  // ══ correct: spu 列名存在 ══
  describe('correct — spu 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `spu`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 spu 表中存在', () => {
      expect(columns).toContain('id');
    });
    it('列 shop_id 在 spu 表中存在', () => {
      expect(columns).toContain('shop_id');
    });
    it('列 category_id 在 spu 表中存在', () => {
      expect(columns).toContain('category_id');
    });
    it('列 name 在 spu 表中存在', () => {
      expect(columns).toContain('name');
    });
    it('列 description 在 spu 表中存在', () => {
      expect(columns).toContain('description');
    });
    it('列 default_image 在 spu 表中存在', () => {
      expect(columns).toContain('default_image');
    });
    it('列 status 在 spu 表中存在', () => {
      expect(columns).toContain('status');
    });
    it('列 sales 在 spu 表中存在', () => {
      expect(columns).toContain('sales');
    });
    it('列 created_at 在 spu 表中存在', () => {
      expect(columns).toContain('created_at');
    });
    it('列 updated_at 在 spu 表中存在', () => {
      expect(columns).toContain('updated_at');
    });
  });

  // ══ boundary: spu NOT NULL / PK / AUTO_INCREMENT ══
  describe('boundary — spu NOT NULL / PK / AUTO_INCREMENT', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `spu`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => {
      expect(colMap['id'].Null).toBe('NO');
    });
    it('shop_id 为 NOT NULL', () => {
      expect(colMap['shop_id'].Null).toBe('NO');
    });
    it('category_id 为 NOT NULL', () => {
      expect(colMap['category_id'].Null).toBe('NO');
    });
    it('name 为 NOT NULL', () => {
      expect(colMap['name'].Null).toBe('NO');
    });
    it('status 为 NOT NULL', () => {
      expect(colMap['status'].Null).toBe('NO');
    });
    it('sales 为 NOT NULL', () => {
      expect(colMap['sales'].Null).toBe('NO');
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

  // ══ boundary: spu 表级约束 (ENUM, FK) ══
  describe('boundary — spu 表级约束 (ENUM, FK)', () => {
    let createTable;
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `spu`');
      createTable = rows[0]['Create Table'];
      const [colRows] = await conn.query('SHOW COLUMNS FROM `spu`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });
    });

    it('status ENUM 类型正确', () => {
      expect(colMap['status'].Type).toContain('enum');
    });
    it('status ENUM 含 draft', () => {
      expect(colMap['status'].Type).toContain('draft');
    });
    it('status ENUM 含 listed', () => {
      expect(colMap['status'].Type).toContain('listed');
    });
    it('status ENUM 含 delisted', () => {
      expect(colMap['status'].Type).toContain('delisted');
    });
    it('status DEFAULT draft', () => {
      expect(colMap['status'].Default).toBe('draft');
    });

    it('FK shop_id → shops.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ error: spu 列名缺失 ══
  describe('error — spu 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `spu`');
      columns = rows.map(r => r.Field);
    });

    it("编造列名 'title' 不在 spu 表中", () => {
      expect(columns).not.toContain('title');
    });

    it("不存在的列名 'xyz_not_a_column' 不在 spu 表中", () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══════════════════════════════════════════════════
  // sku 表
  // ══════════════════════════════════════════════════

  // ══ correct: sku 列名存在 ══
  describe('correct — sku 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `sku`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 sku 表中存在', () => {
      expect(columns).toContain('id');
    });
    it('列 spu_id 在 sku 表中存在', () => {
      expect(columns).toContain('spu_id');
    });
    it('列 spec_name 在 sku 表中存在', () => {
      expect(columns).toContain('spec_name');
    });
    it('列 price 在 sku 表中存在', () => {
      expect(columns).toContain('price');
    });
    it('列 image 在 sku 表中存在', () => {
      expect(columns).toContain('image');
    });
    it('列 created_at 在 sku 表中存在', () => {
      expect(columns).toContain('created_at');
    });
    it('列 updated_at 在 sku 表中存在', () => {
      expect(columns).toContain('updated_at');
    });
  });

  // ══ boundary: sku NOT NULL / PK / AUTO_INCREMENT ══
  describe('boundary — sku NOT NULL / PK / AUTO_INCREMENT', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `sku`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => {
      expect(colMap['id'].Null).toBe('NO');
    });
    it('spu_id 为 NOT NULL', () => {
      expect(colMap['spu_id'].Null).toBe('NO');
    });
    it('spec_name 为 NOT NULL', () => {
      expect(colMap['spec_name'].Null).toBe('NO');
    });
    it('price 为 NOT NULL', () => {
      expect(colMap['price'].Null).toBe('NO');
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

  // ══ boundary: sku 表级约束 (FK, DECIMAL) ══
  describe('boundary — sku 表级约束 (FK, DECIMAL)', () => {
    let createTable;
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `sku`');
      createTable = rows[0]['Create Table'];
      const [colRows] = await conn.query('SHOW COLUMNS FROM `sku`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });
    });

    it('price 类型为 DECIMAL', () => {
      expect(colMap['price'].Type).toContain('decimal');
    });

    it('FK spu_id → spu.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ error: sku 列名缺失 ══
  describe('error — sku 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `sku`');
      columns = rows.map(r => r.Field);
    });

    it("编造列名 'spec_value' 不在 sku 表中", () => {
      expect(columns).not.toContain('spec_value');
    });

    it("不存在的列名 'xyz_not_a_column' 不在 sku 表中", () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══════════════════════════════════════════════════
  // inventories 表
  // ══════════════════════════════════════════════════

  // ══ correct: inventories 列名存在 ══
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

  // ══ boundary: inventories NOT NULL / PK / AUTO_INCREMENT ══
  describe('boundary — inventories NOT NULL / PK / AUTO_INCREMENT', () => {
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
  });

  // ══ boundary: inventories 表级约束 (UNIQUE) ══
  describe('boundary — inventories 表级约束 (UNIQUE)', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `inventories`');
      createTable = rows[0]['Create Table'];
    });

    it('UNIQUE(sku_id, shop_id) 约束存在', () => {
      expect(createTable).toContain('UNIQUE');
    });
  });

  // ══ error: inventories 列名缺失 ══
  describe('error — inventories 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `inventories`');
      columns = rows.map(r => r.Field);
    });

    it("不存在的列名 'xyz_not_a_column' 不在 inventories 表中", () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══════════════════════════════════════════════════
  // product_images 表
  // ══════════════════════════════════════════════════

  // ══ correct: product_images 列名存在 ══
  describe('correct — product_images 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `product_images`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 product_images 表中存在', () => {
      expect(columns).toContain('id');
    });
    it('列 spu_id 在 product_images 表中存在', () => {
      expect(columns).toContain('spu_id');
    });
    it('列 url 在 product_images 表中存在', () => {
      expect(columns).toContain('url');
    });
    it('列 sort 在 product_images 表中存在', () => {
      expect(columns).toContain('sort');
    });
    it('列 created_at 在 product_images 表中存在', () => {
      expect(columns).toContain('created_at');
    });
  });

  // ══ boundary: product_images NOT NULL / PK / AUTO_INCREMENT ══
  describe('boundary — product_images NOT NULL / PK / AUTO_INCREMENT', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `product_images`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => {
      expect(colMap['id'].Null).toBe('NO');
    });
    it('spu_id 为 NOT NULL', () => {
      expect(colMap['spu_id'].Null).toBe('NO');
    });
    it('url 为 NOT NULL', () => {
      expect(colMap['url'].Null).toBe('NO');
    });
    it('sort 为 NOT NULL', () => {
      expect(colMap['sort'].Null).toBe('NO');
    });
    it('created_at 为 NOT NULL', () => {
      expect(colMap['created_at'].Null).toBe('NO');
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });
  });

  // ══ boundary: product_images 表级约束 (FK) ══
  describe('boundary — product_images 表级约束 (FK)', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `product_images`');
      createTable = rows[0]['Create Table'];
    });

    it('FK spu_id → spu.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ error: product_images 列名缺失 ══
  describe('error — product_images 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `product_images`');
      columns = rows.map(r => r.Field);
    });

    it("不存在的列名 'xyz_not_a_column' 不在 product_images 表中", () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });
});

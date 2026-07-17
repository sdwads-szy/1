/** @jest-environment node */
require('dotenv').config();
const mysql = require('mysql2/promise');

describe('t_dbapi_product', () => {
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

  // ══════════════════════════════════════════════
  // spu 表
  // ══════════════════════════════════════════════
  describe('correct — spu 列名存在 (searchProducts / getSpuDetail / getSpuList)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `spu`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 spu 表中存在', () => { expect(columns).toContain('id'); });
    it('列 shop_id 在 spu 表中存在', () => { expect(columns).toContain('shop_id'); });
    it('列 category_id 在 spu 表中存在', () => { expect(columns).toContain('category_id'); });
    it('列 name 在 spu 表中存在', () => { expect(columns).toContain('name'); });
    it('列 description 在 spu 表中存在', () => { expect(columns).toContain('description'); });
    it('列 default_image 在 spu 表中存在', () => { expect(columns).toContain('default_image'); });
    it('列 status 在 spu 表中存在', () => { expect(columns).toContain('status'); });
    it('列 sales 在 spu 表中存在', () => { expect(columns).toContain('sales'); });
    it('列 created_at 在 spu 表中存在', () => { expect(columns).toContain('created_at'); });
  });

  describe('boundary — spu 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `spu`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('shop_id 为 NOT NULL', () => { expect(colMap['shop_id'].Null).toBe('NO'); });
    it('category_id 为 NOT NULL', () => { expect(colMap['category_id'].Null).toBe('NO'); });
    it('name 为 NOT NULL', () => { expect(colMap['name'].Null).toBe('NO'); });
    it('status 为 NOT NULL', () => { expect(colMap['status'].Null).toBe('NO'); });
    it('sales 为 NOT NULL', () => { expect(colMap['sales'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });
  });

  describe('boundary — spu 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `spu`');
      createTable = rows[0]['Create Table'];
    });

    it('FOREIGN KEY shop_id REFERENCES shops', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });

    it('status ENUM 含 draft/listed/delisted', () => {
      expect(createTable).toContain("enum('draft','listed','delisted')");
    });
  });

  describe('error — spu 不存在的列', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `spu`');
      columns = rows.map(r => r.Field);
    });

    it("title 不在 spu DDL 中（DDL 使用 name）", () => {
      expect(columns).not.toContain('title');
    });

    it('xyz_not_a_column 不在 spu 中', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══════════════════════════════════════════════
  // sku 表
  // ══════════════════════════════════════════════
  describe('correct — sku 列名存在 (getSkusBySpu / searchProducts)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `sku`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 sku 表中存在', () => { expect(columns).toContain('id'); });
    it('列 spu_id 在 sku 表中存在', () => { expect(columns).toContain('spu_id'); });
    it('列 spec_name 在 sku 表中存在', () => { expect(columns).toContain('spec_name'); });
    it('列 price 在 sku 表中存在', () => { expect(columns).toContain('price'); });
    it('列 image 在 sku 表中存在', () => { expect(columns).toContain('image'); });
  });

  describe('boundary — sku 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `sku`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('spu_id 为 NOT NULL', () => { expect(colMap['spu_id'].Null).toBe('NO'); });
    it('spec_name 为 NOT NULL', () => { expect(colMap['spec_name'].Null).toBe('NO'); });
    it('price 为 NOT NULL', () => { expect(colMap['price'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });
  });

  describe('boundary — sku 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `sku`');
      createTable = rows[0]['Create Table'];
    });

    it('FOREIGN KEY spu_id REFERENCES spu', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  describe('error — sku 不存在的列', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `sku`');
      columns = rows.map(r => r.Field);
    });

    it('stock 不在 sku DDL 中（库存字段在 inventories 表）', () => {
      expect(columns).not.toContain('stock');
    });

    it('xyz_not_a_column 不在 sku 中', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══════════════════════════════════════════════
  // product_images 表
  // ══════════════════════════════════════════════
  describe('correct — product_images 列名存在 (getProductImages)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `product_images`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 product_images 表中存在', () => { expect(columns).toContain('id'); });
    it('列 spu_id 在 product_images 表中存在', () => { expect(columns).toContain('spu_id'); });
    it('列 url 在 product_images 表中存在', () => { expect(columns).toContain('url'); });
    it('列 sort 在 product_images 表中存在', () => { expect(columns).toContain('sort'); });
  });

  describe('boundary — product_images 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `product_images`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('spu_id 为 NOT NULL', () => { expect(colMap['spu_id'].Null).toBe('NO'); });
    it('url 为 NOT NULL', () => { expect(colMap['url'].Null).toBe('NO'); });
    it('sort 为 NOT NULL', () => { expect(colMap['sort'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });
  });

  describe('boundary — product_images 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `product_images`');
      createTable = rows[0]['Create Table'];
    });

    it('FOREIGN KEY spu_id REFERENCES spu', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══════════════════════════════════════════════
  // categories 表
  // ══════════════════════════════════════════════
  describe('correct — categories 列名存在 (getCategories)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `categories`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 categories 表中存在', () => { expect(columns).toContain('id'); });
    it('列 parent_id 在 categories 表中存在', () => { expect(columns).toContain('parent_id'); });
    it('列 name 在 categories 表中存在', () => { expect(columns).toContain('name'); });
    it('列 level 在 categories 表中存在', () => { expect(columns).toContain('level'); });
    it('列 sort 在 categories 表中存在', () => { expect(columns).toContain('sort'); });
    it('列 icon 在 categories 表中存在', () => { expect(columns).toContain('icon'); });
  });

  describe('boundary — categories 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `categories`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('name 为 NOT NULL', () => { expect(colMap['name'].Null).toBe('NO'); });
    it('level 为 NOT NULL', () => { expect(colMap['level'].Null).toBe('NO'); });
    it('sort 为 NOT NULL', () => { expect(colMap['sort'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });
  });

  describe('boundary — categories 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `categories`');
      createTable = rows[0]['Create Table'];
    });

    it('FOREIGN KEY parent_id REFERENCES categories', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══════════════════════════════════════════════
  // shops 表
  // ══════════════════════════════════════════════
  describe('correct — shops 列名存在 (getShopById / searchProducts)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shops`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 shops 表中存在', () => { expect(columns).toContain('id'); });
    it('列 merchant_id 在 shops 表中存在', () => { expect(columns).toContain('merchant_id'); });
    it('列 name 在 shops 表中存在', () => { expect(columns).toContain('name'); });
    it('列 logo 在 shops 表中存在', () => { expect(columns).toContain('logo'); });
    it('列 banner 在 shops 表中存在', () => { expect(columns).toContain('banner'); });
    it('列 description 在 shops 表中存在', () => { expect(columns).toContain('description'); });
    it('列 status 在 shops 表中存在', () => { expect(columns).toContain('status'); });
  });

  describe('boundary — shops 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shops`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('merchant_id 为 NOT NULL', () => { expect(colMap['merchant_id'].Null).toBe('NO'); });
    it('name 为 NOT NULL', () => { expect(colMap['name'].Null).toBe('NO'); });
    it('status 为 NOT NULL', () => { expect(colMap['status'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });
  });

  describe('boundary — shops 表级约束 (ENUM / FK / UNIQUE)', () => {
    let createTable;
    let colMap;
    beforeAll(async () => {
      const [createRows] = await conn.query('SHOW CREATE TABLE `shops`');
      createTable = createRows[0]['Create Table'];
      const [colRows] = await conn.query('SHOW COLUMNS FROM `shops`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });
    });

    it('merchant_id 为 UNIQUE', () => {
      expect(colMap['merchant_id'].Key).toBe('UNI');
    });

    it('name 为 UNIQUE', () => {
      expect(colMap['name'].Key).toBe('UNI');
    });

    it('FOREIGN KEY merchant_id REFERENCES merchants', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });

    it("status ENUM 含 'open','closed','frozen'", () => {
      expect(createTable).toContain("enum('open','closed','frozen')");
    });
  });
});

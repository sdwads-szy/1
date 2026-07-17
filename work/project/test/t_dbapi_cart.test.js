/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_cart', () => {
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

  // ══ correct: upsertCartItem INSERT INTO cart_items ... ON DUPLICATE KEY UPDATE ══
  describe('correct — upsertCartItem INSERT 列名对齐', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `cart_items`');
      columns = rows.map(r => r.Field);
    });

    it('user_id 在 cart_items 中存在', () => { expect(columns).toContain('user_id'); });
    it('sku_id 在 cart_items 中存在', () => { expect(columns).toContain('sku_id'); });
    it('shop_id 在 cart_items 中存在', () => { expect(columns).toContain('shop_id'); });
    it('quantity 在 cart_items 中存在', () => { expect(columns).toContain('quantity'); });
    it('checked 在 cart_items 中存在', () => { expect(columns).toContain('checked'); });
  });

  // ══ correct: getCartItems SELECT FROM cart_items ══
  describe('correct — getCartItems SELECT 列名对齐', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `cart_items`');
      columns = rows.map(r => r.Field);
    });

    it('id 在 cart_items 中存在', () => { expect(columns).toContain('id'); });
    it('user_id 在 cart_items 中存在', () => { expect(columns).toContain('user_id'); });
    it('sku_id 在 cart_items 中存在', () => { expect(columns).toContain('sku_id'); });
    it('shop_id 在 cart_items 中存在', () => { expect(columns).toContain('shop_id'); });
    it('quantity 在 cart_items 中存在', () => { expect(columns).toContain('quantity'); });
    it('checked 在 cart_items 中存在', () => { expect(columns).toContain('checked'); });
    it('created_at 在 cart_items 中存在', () => { expect(columns).toContain('created_at'); });
  });

  // ══ correct: updateCartChecked UPDATE cart_items ══
  describe('correct — updateCartChecked UPDATE 列名对齐', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `cart_items`');
      columns = rows.map(r => r.Field);
    });

    it('checked 在 cart_items 中存在', () => { expect(columns).toContain('checked'); });
    it('user_id 在 cart_items 中存在', () => { expect(columns).toContain('user_id'); });
    it('sku_id 在 cart_items 中存在', () => { expect(columns).toContain('sku_id'); });
  });

  // ══ correct: deleteCartItems DELETE FROM cart_items ══
  describe('correct — deleteCartItems DELETE 列名对齐', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `cart_items`');
      columns = rows.map(r => r.Field);
    });

    it('user_id 在 cart_items 中存在', () => { expect(columns).toContain('user_id'); });
    it('sku_id 在 cart_items 中存在', () => { expect(columns).toContain('sku_id'); });
  });

  // ══ error: 编造列名 product_id 不在 cart_items DDL 中 ══
  describe('error — 编造列名不在 DDL 中', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `cart_items`');
      columns = rows.map(r => r.Field);
    });

    it('product_id 不在 cart_items DDL 字段列表中（DDL 使用 sku_id）', () => {
      expect(columns).not.toContain('product_id');
    });
  });

  // ══ boundary: NOT NULL / PK / AUTO_INCREMENT / DEFAULT（SHOW COLUMNS）══
  describe('boundary — cart_items 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `cart_items`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('user_id 为 NOT NULL', () => { expect(colMap['user_id'].Null).toBe('NO'); });
    it('sku_id 为 NOT NULL', () => { expect(colMap['sku_id'].Null).toBe('NO'); });
    it('shop_id 为 NOT NULL', () => { expect(colMap['shop_id'].Null).toBe('NO'); });
    it('quantity 为 NOT NULL', () => { expect(colMap['quantity'].Null).toBe('NO'); });
    it('checked 为 NOT NULL', () => { expect(colMap['checked'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    it('quantity DEFAULT 1', () => {
      expect(colMap['quantity'].Default).toBe('1');
    });

    it('checked DEFAULT 1', () => {
      expect(colMap['checked'].Default).toBe('1');
    });
  });

  // ══ boundary: UNIQUE / FK 表级约束（SHOW CREATE TABLE）══
  describe('boundary — cart_items 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `cart_items`');
      createTable = rows[0]['Create Table'];
    });

    it('UNIQUE KEY idx_user_sku_shop (user_id, sku_id, shop_id) 存在', () => {
      expect(createTable).toContain('UNIQUE');
      expect(createTable).toContain('idx_user_sku_shop');
    });

    it('FOREIGN KEY fk_cart_items_user (user_id→users.id) 存在', () => {
      expect(createTable).toContain('fk_cart_items_user');
    });

    it('FOREIGN KEY fk_cart_items_sku (sku_id→sku.id) 存在', () => {
      expect(createTable).toContain('fk_cart_items_sku');
    });

    it('FOREIGN KEY fk_cart_items_shop (shop_id→shops.id) 存在', () => {
      expect(createTable).toContain('fk_cart_items_shop');
    });
  });
});

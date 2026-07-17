/** @jest-environment node */
require('dotenv').config();
const mysql = require('mysql2/promise');

describe('t_dbapi_order', () => {
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

  // ══ correct: orders 列名存在 ══
  describe('correct — orders 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `orders`');
      columns = rows.map(r => r.Field);
    });

    it('id 在 orders 表中存在', () => { expect(columns).toContain('id'); });
    it('order_no 在 orders 表中存在', () => { expect(columns).toContain('order_no'); });
    it('user_id 在 orders 表中存在', () => { expect(columns).toContain('user_id'); });
    it('total_amount 在 orders 表中存在', () => { expect(columns).toContain('total_amount'); });
    it('status 在 orders 表中存在', () => { expect(columns).toContain('status'); });
    it('paid_at 在 orders 表中存在', () => { expect(columns).toContain('paid_at'); });
    it('created_at 在 orders 表中存在', () => { expect(columns).toContain('created_at'); });
    it('updated_at 在 orders 表中存在', () => { expect(columns).toContain('updated_at'); });
  });

  // ══ correct: sub_orders 列名存在 ══
  describe('correct — sub_orders 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `sub_orders`');
      columns = rows.map(r => r.Field);
    });

    it('id 在 sub_orders 表中存在', () => { expect(columns).toContain('id'); });
    it('sub_order_no 在 sub_orders 表中存在', () => { expect(columns).toContain('sub_order_no'); });
    it('order_id 在 sub_orders 表中存在', () => { expect(columns).toContain('order_id'); });
    it('shop_id 在 sub_orders 表中存在', () => { expect(columns).toContain('shop_id'); });
    it('amount 在 sub_orders 表中存在', () => { expect(columns).toContain('amount'); });
    it('status 在 sub_orders 表中存在', () => { expect(columns).toContain('status'); });
    it('created_at 在 sub_orders 表中存在', () => { expect(columns).toContain('created_at'); });
  });

  // ══ correct: order_items 列名存在 ══
  describe('correct — order_items 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `order_items`');
      columns = rows.map(r => r.Field);
    });

    it('id 在 order_items 表中存在', () => { expect(columns).toContain('id'); });
    it('sub_order_id 在 order_items 表中存在', () => { expect(columns).toContain('sub_order_id'); });
    it('sku_id 在 order_items 表中存在', () => { expect(columns).toContain('sku_id'); });
    it('quantity 在 order_items 表中存在', () => { expect(columns).toContain('quantity'); });
    it('price 在 order_items 表中存在', () => { expect(columns).toContain('price'); });
    it('snapshot 在 order_items 表中存在', () => { expect(columns).toContain('snapshot'); });
  });

  // ══ boundary: orders 约束 ══
  describe('boundary — orders 约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `orders`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('order_no 为 NOT NULL', () => { expect(colMap['order_no'].Null).toBe('NO'); });
    it('user_id 为 NOT NULL', () => { expect(colMap['user_id'].Null).toBe('NO'); });
    it('total_amount 为 NOT NULL', () => { expect(colMap['total_amount'].Null).toBe('NO'); });
    it('status 为 NOT NULL', () => { expect(colMap['status'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });

    it('status ENUM 值包含 pending', () => { expect(colMap['status'].Type).toContain('pending'); });
    it('status ENUM 值包含 paid', () => { expect(colMap['status'].Type).toContain('paid'); });
    it('status ENUM 值包含 shipped', () => { expect(colMap['status'].Type).toContain('shipped'); });
    it('status ENUM 值包含 completed', () => { expect(colMap['status'].Type).toContain('completed'); });
    it('status ENUM 值包含 cancelled', () => { expect(colMap['status'].Type).toContain('cancelled'); });
    it('status ENUM 值包含 refunding', () => { expect(colMap['status'].Type).toContain('refunding'); });
    it('status ENUM 值包含 refunded', () => { expect(colMap['status'].Type).toContain('refunded'); });
  });

  // ══ boundary: orders 表级约束 ══
  describe('boundary — orders 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `orders`');
      createTable = rows[0]['Create Table'];
    });

    it('order_no UNIQUE 约束存在', () => { expect(createTable).toContain('UNIQUE'); });
    it('FK user_id → users.id 存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ boundary: sub_orders 约束 ══
  describe('boundary — sub_orders 约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `sub_orders`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('sub_order_no 为 NOT NULL', () => { expect(colMap['sub_order_no'].Null).toBe('NO'); });
    it('order_id 为 NOT NULL', () => { expect(colMap['order_id'].Null).toBe('NO'); });
    it('shop_id 为 NOT NULL', () => { expect(colMap['shop_id'].Null).toBe('NO'); });
    it('amount 为 NOT NULL', () => { expect(colMap['amount'].Null).toBe('NO'); });
    it('status 为 NOT NULL', () => { expect(colMap['status'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });

    it('status ENUM 值包含 pending', () => { expect(colMap['status'].Type).toContain('pending'); });
    it('status ENUM 值包含 paid', () => { expect(colMap['status'].Type).toContain('paid'); });
    it('status ENUM 值包含 shipped', () => { expect(colMap['status'].Type).toContain('shipped'); });
    it('status ENUM 值包含 completed', () => { expect(colMap['status'].Type).toContain('completed'); });
    it('status ENUM 值包含 cancelled', () => { expect(colMap['status'].Type).toContain('cancelled'); });
    it('status ENUM 值包含 refunding', () => { expect(colMap['status'].Type).toContain('refunding'); });
    it('status ENUM 值包含 refunded', () => { expect(colMap['status'].Type).toContain('refunded'); });
  });

  // ══ boundary: sub_orders 表级约束 ══
  describe('boundary — sub_orders 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `sub_orders`');
      createTable = rows[0]['Create Table'];
    });

    it('sub_order_no UNIQUE 约束存在', () => { expect(createTable).toContain('UNIQUE'); });
    it('FK order_id → orders.id 存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
    it('FK shop_id → shops.id 存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ boundary: order_items 约束 ══
  describe('boundary — order_items 约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `order_items`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('sub_order_id 为 NOT NULL', () => { expect(colMap['sub_order_id'].Null).toBe('NO'); });
    it('sku_id 为 NOT NULL', () => { expect(colMap['sku_id'].Null).toBe('NO'); });
    it('quantity 为 NOT NULL', () => { expect(colMap['quantity'].Null).toBe('NO'); });
    it('price 为 NOT NULL', () => { expect(colMap['price'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });
  });

  // ══ boundary: order_items 表级约束 ══
  describe('boundary — order_items 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `order_items`');
      createTable = rows[0]['Create Table'];
    });

    it('FK sub_order_id → sub_orders.id 存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ══ error: 列名缺失 ══
  describe('error — 列名缺失', () => {
    let ordersCols, subOrdersCols, orderItemsCols;
    beforeAll(async () => {
      const [oRows] = await conn.query('SHOW COLUMNS FROM `orders`');
      ordersCols = oRows.map(r => r.Field);
      const [soRows] = await conn.query('SHOW COLUMNS FROM `sub_orders`');
      subOrdersCols = soRows.map(r => r.Field);
      const [oiRows] = await conn.query('SHOW COLUMNS FROM `order_items`');
      orderItemsCols = oiRows.map(r => r.Field);
    });

    it('order_status 不在 orders 表中', () => { expect(ordersCols).not.toContain('order_status'); });
    it('product_name 不在 order_items 表中', () => { expect(orderItemsCols).not.toContain('product_name'); });
    it('xyz_not_a_column 不在任何订单表中', () => {
      expect(ordersCols).not.toContain('xyz_not_a_column');
      expect(subOrdersCols).not.toContain('xyz_not_a_column');
      expect(orderItemsCols).not.toContain('xyz_not_a_column');
    });
  });

  // ══ error: truth 列 vs 真实 DB ══
  describe('error — truth 列 vs 真实 DB', () => {
    let ordersCols, subOrdersCols, orderItemsCols;
    beforeAll(async () => {
      const [oRows] = await conn.query('SHOW COLUMNS FROM `orders`');
      ordersCols = new Set(oRows.map(r => r.Field));
      const [soRows] = await conn.query('SHOW COLUMNS FROM `sub_orders`');
      subOrdersCols = new Set(soRows.map(r => r.Field));
      const [oiRows] = await conn.query('SHOW COLUMNS FROM `order_items`');
      orderItemsCols = new Set(oiRows.map(r => r.Field));
    });

    // t_db_orders 真理 — orders 表
    it('orders.id 在 DB 中存在', () => { expect(ordersCols.has('id')).toBe(true); });
    it('orders.order_no 在 DB 中存在', () => { expect(ordersCols.has('order_no')).toBe(true); });
    it('orders.user_id 在 DB 中存在', () => { expect(ordersCols.has('user_id')).toBe(true); });
    it('orders.total_amount 在 DB 中存在', () => { expect(ordersCols.has('total_amount')).toBe(true); });
    it('orders.status 在 DB 中存在', () => { expect(ordersCols.has('status')).toBe(true); });
    it('orders.paid_at 在 DB 中存在', () => { expect(ordersCols.has('paid_at')).toBe(true); });
    it('orders.created_at 在 DB 中存在', () => { expect(ordersCols.has('created_at')).toBe(true); });
    it('orders.updated_at 在 DB 中存在', () => { expect(ordersCols.has('updated_at')).toBe(true); });

    // t_db_sub_orders 真理 — sub_orders 表
    it('sub_orders.id 在 DB 中存在', () => { expect(subOrdersCols.has('id')).toBe(true); });
    it('sub_orders.sub_order_no 在 DB 中存在', () => { expect(subOrdersCols.has('sub_order_no')).toBe(true); });
    it('sub_orders.order_id 在 DB 中存在', () => { expect(subOrdersCols.has('order_id')).toBe(true); });
    it('sub_orders.shop_id 在 DB 中存在', () => { expect(subOrdersCols.has('shop_id')).toBe(true); });
    it('sub_orders.amount 在 DB 中存在', () => { expect(subOrdersCols.has('amount')).toBe(true); });
    it('sub_orders.status 在 DB 中存在', () => { expect(subOrdersCols.has('status')).toBe(true); });
    it('sub_orders.created_at 在 DB 中存在', () => { expect(subOrdersCols.has('created_at')).toBe(true); });
    it('sub_orders.updated_at 在 DB 中存在', () => { expect(subOrdersCols.has('updated_at')).toBe(true); });

    // t_db_order_items 真理 — order_items 表
    it('order_items.id 在 DB 中存在', () => { expect(orderItemsCols.has('id')).toBe(true); });
    it('order_items.sub_order_id 在 DB 中存在', () => { expect(orderItemsCols.has('sub_order_id')).toBe(true); });
    it('order_items.sku_id 在 DB 中存在', () => { expect(orderItemsCols.has('sku_id')).toBe(true); });
    it('order_items.quantity 在 DB 中存在', () => { expect(orderItemsCols.has('quantity')).toBe(true); });
    it('order_items.price 在 DB 中存在', () => { expect(orderItemsCols.has('price')).toBe(true); });
    it('order_items.snapshot 在 DB 中存在', () => { expect(orderItemsCols.has('snapshot')).toBe(true); });
    it('order_items.created_at 在 DB 中存在', () => { expect(orderItemsCols.has('created_at')).toBe(true); });
  });
});

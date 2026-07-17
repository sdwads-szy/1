/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_shipment', () => {
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

  // ═══════════════════════════════════════════════
  // correct — shipments 列名存在
  // ═══════════════════════════════════════════════
  describe('correct — shipments 列名存在 (SHOW COLUMNS)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shipments`');
      columns = rows.map(r => r.Field);
    });

    const expectedShipmentsCols = [
      'id',
      'sub_order_id',
      'tracking_no',
      'carrier_code',
      'status',
      'created_at',
      'updated_at',
    ];

    expectedShipmentsCols.forEach(col => {
      it(`列 ${col} 在 shipments 表中存在`, () => {
        expect(columns).toContain(col);
      });
    });
  });

  // ═══════════════════════════════════════════════
  // correct — shipment_events 列名存在
  // ═══════════════════════════════════════════════
  describe('correct — shipment_events 列名存在 (SHOW COLUMNS)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shipment_events`');
      columns = rows.map(r => r.Field);
    });

    const expectedEventCols = [
      'id',
      'shipment_id',
      'event',
      'timestamp',
      'location',
      'created_at',
    ];

    expectedEventCols.forEach(col => {
      it(`列 ${col} 在 shipment_events 表中存在`, () => {
        expect(columns).toContain(col);
      });
    });
  });

  // ═══════════════════════════════════════════════
  // boundary — shipments 列级约束 (NOT NULL / PK / AUTO_INCREMENT)
  // ═══════════════════════════════════════════════
  describe('boundary — shipments 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shipments`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('sub_order_id 为 NOT NULL', () => {
      expect(colMap['sub_order_id'].Null).toBe('NO');
    });

    it('tracking_no 为 NOT NULL', () => {
      expect(colMap['tracking_no'].Null).toBe('NO');
    });

    it('carrier_code 为 NOT NULL', () => {
      expect(colMap['carrier_code'].Null).toBe('NO');
    });

    it('status 为 NOT NULL', () => {
      expect(colMap['status'].Null).toBe('NO');
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

  // ═══════════════════════════════════════════════
  // boundary — shipment_events 列级约束 (NOT NULL / PK / AUTO_INCREMENT)
  // ═══════════════════════════════════════════════
  describe('boundary — shipment_events 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shipment_events`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('event 为 NOT NULL', () => {
      expect(colMap['event'].Null).toBe('NO');
    });

    it('timestamp 为 NOT NULL', () => {
      expect(colMap['timestamp'].Null).toBe('NO');
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });
  });

  // ═══════════════════════════════════════════════
  // boundary — shipments 表级约束 (ENUM / FK / INDEX)
  // ═══════════════════════════════════════════════
  describe('boundary — shipments 表级约束 (SHOW CREATE TABLE)', () => {
    let createTable;
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `shipments`');
      createTable = rows[0]['Create Table'];

      const [colRows] = await conn.query('SHOW COLUMNS FROM `shipments`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });
    });

    it("status ENUM 值包含 'pending_pickup'", () => {
      expect(colMap['status'].Type).toContain('enum');
      expect(colMap['status'].Type).toContain('pending_pickup');
    });

    it("status ENUM 值包含 'in_transit'", () => {
      expect(colMap['status'].Type).toContain('in_transit');
    });

    it("status ENUM 值包含 'delivered'", () => {
      expect(colMap['status'].Type).toContain('delivered');
    });

    it("status ENUM 值包含 'returned'", () => {
      expect(colMap['status'].Type).toContain('returned');
    });

    it("status DEFAULT 'pending_pickup'", () => {
      expect(colMap['status'].Default).toBe('pending_pickup');
    });

    it('FK 约束 FOREIGN KEY 存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
    });

    it('FK 约束 REFERENCES 存在', () => {
      expect(createTable).toContain('REFERENCES');
    });

    it('索引 idx_sub_order_id 存在', () => {
      expect(createTable).toContain('idx_sub_order_id');
    });

    it('索引 idx_tracking_no 存在', () => {
      expect(createTable).toContain('idx_tracking_no');
    });
  });

  // ═══════════════════════════════════════════════
  // boundary — shipment_events 表级约束 (FK / INDEX)
  // ═══════════════════════════════════════════════
  describe('boundary — shipment_events 表级约束 (SHOW CREATE TABLE)', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `shipment_events`');
      createTable = rows[0]['Create Table'];
    });

    it('FK 约束 FOREIGN KEY 存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
    });

    it('FK 约束 REFERENCES 存在', () => {
      expect(createTable).toContain('REFERENCES');
    });

    it('索引 idx_shipment_id 存在', () => {
      expect(createTable).toContain('idx_shipment_id');
    });

    it('索引 idx_shipment_timestamp 存在', () => {
      expect(createTable).toContain('idx_shipment_timestamp');
    });
  });

  // ═══════════════════════════════════════════════
  // error — 列名缺失（编造列名不在 DDL 中）
  // ═══════════════════════════════════════════════
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shipments`');
      columns = rows.map(r => r.Field);
    });

    it("'logistics_status' 不在 shipments DDL 中（DDL 使用 status）", () => {
      expect(columns).not.toContain('logistics_status');
    });
  });

  // ═══════════════════════════════════════════════
  // error — truth 列 vs 真实 DB（DDL 声明的列在数据库中真实存在）
  // ═══════════════════════════════════════════════
  describe('error — truth shipments 列 vs 真实 DB', () => {
    let allColumns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shipments`');
      allColumns = new Set(rows.map(r => r.Field));
    });

    const truthShipmentsCols = [
      'id',
      'sub_order_id',
      'tracking_no',
      'carrier_code',
      'status',
      'created_at',
      'updated_at',
    ];

    truthShipmentsCols.forEach(col => {
      it(`truth 列 ${col} 在 DB shipments 中存在`, () => {
        expect(allColumns.has(col)).toBe(true);
      });
    });
  });

  describe('error — truth shipment_events 列 vs 真实 DB', () => {
    let allColumns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shipment_events`');
      allColumns = new Set(rows.map(r => r.Field));
    });

    const truthEventCols = [
      'id',
      'shipment_id',
      'event',
      'timestamp',
      'location',
      'created_at',
    ];

    truthEventCols.forEach(col => {
      it(`truth 列 ${col} 在 DB shipment_events 中存在`, () => {
        expect(allColumns.has(col)).toBe(true);
      });
    });
  });
});

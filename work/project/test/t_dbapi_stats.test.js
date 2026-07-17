/** @jest-environment node */
require('dotenv').config();
const mysql = require('mysql2/promise');

describe('t_dbapi_stats', () => {
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

  // ═══════════════════════════════════════════════════
  // correct: merchant_daily_stats 列名存在
  // ═══════════════════════════════════════════════════
  describe('correct — merchant_daily_stats 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `merchant_daily_stats`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 merchant_daily_stats 表中存在', () => {
      expect(columns).toContain('id');
    });
    it('列 merchant_id 在 merchant_daily_stats 表中存在', () => {
      expect(columns).toContain('merchant_id');
    });
    it('列 stat_date 在 merchant_daily_stats 表中存在', () => {
      expect(columns).toContain('stat_date');
    });
    it('列 gmv 在 merchant_daily_stats 表中存在', () => {
      expect(columns).toContain('gmv');
    });
    it('列 order_count 在 merchant_daily_stats 表中存在', () => {
      expect(columns).toContain('order_count');
    });
  });

  // ═══════════════════════════════════════════════════
  // correct: platform_daily_stats 列名存在
  // ═══════════════════════════════════════════════════
  describe('correct — platform_daily_stats 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `platform_daily_stats`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 platform_daily_stats 表中存在', () => {
      expect(columns).toContain('id');
    });
    it('列 stat_date 在 platform_daily_stats 表中存在', () => {
      expect(columns).toContain('stat_date');
    });
    it('列 gmv 在 platform_daily_stats 表中存在', () => {
      expect(columns).toContain('gmv');
    });
    it('列 order_count 在 platform_daily_stats 表中存在', () => {
      expect(columns).toContain('order_count');
    });
    it('列 paid_order_count 在 platform_daily_stats 表中存在', () => {
      expect(columns).toContain('paid_order_count');
    });
    it('列 refund_rate 在 platform_daily_stats 表中存在', () => {
      expect(columns).toContain('refund_rate');
    });
    it('列 commission 在 platform_daily_stats 表中存在', () => {
      expect(columns).toContain('commission');
    });
  });

  // ═══════════════════════════════════════════════════
  // boundary: merchant_daily_stats 约束
  // ═══════════════════════════════════════════════════
  describe('boundary — merchant_daily_stats 约束', () => {
    let colMap;
    let createTable;
    beforeAll(async () => {
      const [colRows] = await conn.query('SHOW COLUMNS FROM `merchant_daily_stats`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });

      const [createRows] = await conn.query('SHOW CREATE TABLE `merchant_daily_stats`');
      createTable = createRows[0]['Create Table'];
    });

    // NOT NULL
    it('merchant_id 为 NOT NULL', () => {
      expect(colMap['merchant_id'].Null).toBe('NO');
    });
    it('stat_date 为 NOT NULL', () => {
      expect(colMap['stat_date'].Null).toBe('NO');
    });
    it('gmv 为 NOT NULL', () => {
      expect(colMap['gmv'].Null).toBe('NO');
    });
    it('order_count 为 NOT NULL', () => {
      expect(colMap['order_count'].Null).toBe('NO');
    });

    // PK
    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    // AUTO_INCREMENT
    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    // gmv DECIMAL(10,2)
    it('gmv 类型为 DECIMAL(10,2)', () => {
      expect(colMap['gmv'].Type).toContain('decimal(10,2)');
    });

    // order_count DEFAULT 0
    it('order_count DEFAULT 0', () => {
      expect(String(colMap['order_count'].Default)).toBe('0');
    });
  });

  // ═══════════════════════════════════════════════════
  // boundary: merchant_daily_stats 表级约束
  // ═══════════════════════════════════════════════════
  describe('boundary — merchant_daily_stats 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `merchant_daily_stats`');
      createTable = rows[0]['Create Table'];
    });

    it('UNIQUE(merchant_id, stat_date) 约束存在', () => {
      expect(createTable).toContain('UNIQUE');
    });

    it('FOREIGN KEY merchant_id REFERENCES merchants(id)', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ═══════════════════════════════════════════════════
  // boundary: platform_daily_stats 约束
  // ═══════════════════════════════════════════════════
  describe('boundary — platform_daily_stats 约束', () => {
    let colMap;
    let createTable;
    beforeAll(async () => {
      const [colRows] = await conn.query('SHOW COLUMNS FROM `platform_daily_stats`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });

      const [createRows] = await conn.query('SHOW CREATE TABLE `platform_daily_stats`');
      createTable = createRows[0]['Create Table'];
    });

    // NOT NULL
    it('stat_date 为 NOT NULL', () => {
      expect(colMap['stat_date'].Null).toBe('NO');
    });
    it('gmv 为 NOT NULL', () => {
      expect(colMap['gmv'].Null).toBe('NO');
    });
    it('order_count 为 NOT NULL', () => {
      expect(colMap['order_count'].Null).toBe('NO');
    });
    it('paid_order_count 为 NOT NULL', () => {
      expect(colMap['paid_order_count'].Null).toBe('NO');
    });
    it('refund_rate 为 NOT NULL', () => {
      expect(colMap['refund_rate'].Null).toBe('NO');
    });
    it('commission 为 NOT NULL', () => {
      expect(colMap['commission'].Null).toBe('NO');
    });

    // PK
    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    // AUTO_INCREMENT
    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    // stat_date UNIQUE
    it('stat_date UNIQUE 约束存在', () => {
      expect(createTable).toContain('UNIQUE');
    });

    // gmv DECIMAL(12,2)
    it('gmv 类型为 DECIMAL(12,2)', () => {
      expect(colMap['gmv'].Type).toContain('decimal(12,2)');
    });

    // refund_rate DECIMAL(5,4)
    it('refund_rate 类型为 DECIMAL(5,4)', () => {
      expect(colMap['refund_rate'].Type).toContain('decimal(5,4)');
    });

    // commission DECIMAL(10,2)
    it('commission 类型为 DECIMAL(10,2)', () => {
      expect(colMap['commission'].Type).toContain('decimal(10,2)');
    });

    // DEFAULT 值
    it('gmv DEFAULT 0.00', () => {
      expect(String(colMap['gmv'].Default)).toContain('0.00');
    });
    it('order_count DEFAULT 0', () => {
      expect(String(colMap['order_count'].Default)).toBe('0');
    });
    it('paid_order_count DEFAULT 0', () => {
      expect(String(colMap['paid_order_count'].Default)).toBe('0');
    });
    it('refund_rate DEFAULT 0.0000', () => {
      expect(String(colMap['refund_rate'].Default)).toContain('0.0000');
    });
    it('commission DEFAULT 0.00', () => {
      expect(String(colMap['commission'].Default)).toContain('0.00');
    });
  });

  // ═══════════════════════════════════════════════════
  // error: 列名缺失
  // ═══════════════════════════════════════════════════
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `platform_daily_stats`');
      columns = rows.map(r => r.Field);
    });

    it("'revenue' 不在 platform_daily_stats 表中（DDL 使用 gmv）", () => {
      expect(columns).not.toContain('revenue');
    });

    it('不存在的列名 xyz_not_a_column 不在表中', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ═══════════════════════════════════════════════════
  // error: merchant_daily_stats 编造列名
  // ═══════════════════════════════════════════════════
  describe('error — merchant_daily_stats 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `merchant_daily_stats`');
      columns = rows.map(r => r.Field);
    });

    it('不存在的列名 revenue 不在 merchant_daily_stats 表中', () => {
      expect(columns).not.toContain('revenue');
    });

    it('不存在的列名 abc_not_a_column 不在 merchant_daily_stats 表中', () => {
      expect(columns).not.toContain('abc_not_a_column');
    });
  });
});

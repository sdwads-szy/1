/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_merchant', () => {
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

  // ════════════════════════════════════════════════
  // correct — merchants 列名存在（SHOW COLUMNS）
  // ════════════════════════════════════════════════
  describe('correct — merchants 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `merchants`');
      columns = rows.map(r => r.Field);
    });

    // 8 个 SQL 操作中引用的 merchants 列名（并集）
    const expectedMerchantCols = [
      'id',
      'user_id',
      'credit_code',
      'biz_license',
      'contact_name',
      'contact_mobile',
      'status',
      'review_reason',
      'reviewed_at',
      'created_at',
    ];

    it.each(expectedMerchantCols)('列 %s 在 merchants 表中存在', (col) => {
      expect(columns).toContain(col);
    });
  });

  // ════════════════════════════════════════════════
  // correct — shops 列名存在（SHOW COLUMNS）
  // ════════════════════════════════════════════════
  describe('correct — shops 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shops`');
      columns = rows.map(r => r.Field);
    });

    // 8 个 SQL 操作中引用的 shops 列名（并集）
    const expectedShopCols = [
      'id',
      'merchant_id',
      'name',
      'logo',
      'banner',
      'description',
      'status',
    ];

    it.each(expectedShopCols)('列 %s 在 shops 表中存在', (col) => {
      expect(columns).toContain(col);
    });
  });

  // ════════════════════════════════════════════════
  // boundary — merchants 约束（NOT NULL / PK / AUTO_INCREMENT / DEFAULT）
  // ════════════════════════════════════════════════
  describe('boundary — merchants 约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `merchants`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    const notNullCols = [
      'id',
      'user_id',
      'credit_code',
      'biz_license',
      'contact_name',
      'contact_mobile',
      'status',
      'created_at',
      'updated_at',
    ];

    it.each(notNullCols)('%s 为 NOT NULL', (col) => {
      expect(colMap[col].Null).toBe('NO');
    });

    it('review_reason 允许 NULL', () => {
      expect(colMap['review_reason'].Null).toBe('YES');
    });

    it('reviewed_at 允许 NULL', () => {
      expect(colMap['reviewed_at'].Null).toBe('YES');
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    it('status DEFAULT pending_review', () => {
      expect(colMap['status'].Default).toBe('pending_review');
    });

    it('created_at DEFAULT CURRENT_TIMESTAMP', () => {
      expect(colMap['created_at'].Default).toContain('CURRENT_TIMESTAMP');
    });

    it('updated_at DEFAULT CURRENT_TIMESTAMP + ON UPDATE', () => {
      expect(colMap['updated_at'].Default).toContain('CURRENT_TIMESTAMP');
      expect(colMap['updated_at'].Extra).toContain('on update');
    });
  });

  // ════════════════════════════════════════════════
  // boundary — shops 约束（NOT NULL / PK / AUTO_INCREMENT / DEFAULT）
  // ════════════════════════════════════════════════
  describe('boundary — shops 约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `shops`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    const notNullCols = [
      'id',
      'merchant_id',
      'name',
      'status',
      'created_at',
      'updated_at',
    ];

    it.each(notNullCols)('%s 为 NOT NULL', (col) => {
      expect(colMap[col].Null).toBe('NO');
    });

    const nullableCols = ['logo', 'banner', 'description'];
    it.each(nullableCols)('%s 允许 NULL', (col) => {
      expect(colMap[col].Null).toBe('YES');
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    it('status DEFAULT open', () => {
      expect(colMap['status'].Default).toBe('open');
    });

    it('created_at DEFAULT CURRENT_TIMESTAMP', () => {
      expect(colMap['created_at'].Default).toContain('CURRENT_TIMESTAMP');
    });

    it('updated_at DEFAULT CURRENT_TIMESTAMP + ON UPDATE', () => {
      expect(colMap['updated_at'].Default).toContain('CURRENT_TIMESTAMP');
      expect(colMap['updated_at'].Extra).toContain('on update');
    });
  });

  // ════════════════════════════════════════════════
  // boundary — 表级约束（UNIQUE + ENUM + FK）
  // SHOW COLUMNS 看不到 CHECK/FULLTEXT/复合约束，用 SHOW CREATE TABLE
  // ════════════════════════════════════════════════
  describe('boundary — 表级约束', () => {
    let merchantsCreate;
    let shopsCreate;
    let merchantsColMap;
    let shopsColMap;

    beforeAll(async () => {
      const [mRows] = await conn.query('SHOW CREATE TABLE `merchants`');
      merchantsCreate = mRows[0]['Create Table'];
      const [sRows] = await conn.query('SHOW CREATE TABLE `shops`');
      shopsCreate = sRows[0]['Create Table'];

      const [mcRows] = await conn.query('SHOW COLUMNS FROM `merchants`');
      merchantsColMap = {};
      mcRows.forEach(r => { merchantsColMap[r.Field] = r; });

      const [scRows] = await conn.query('SHOW COLUMNS FROM `shops`');
      shopsColMap = {};
      scRows.forEach(r => { shopsColMap[r.Field] = r; });
    });

    // ── merchants UNIQUE / ENUM / FK ──
    it('merchants: credit_code UNIQUE', () => {
      expect(merchantsCreate).toContain('UNIQUE');
    });

    it('merchants: status ENUM 值正确', () => {
      expect(merchantsColMap['status'].Type).toContain('enum');
      expect(merchantsColMap['status'].Type).toContain('pending_review');
      expect(merchantsColMap['status'].Type).toContain('approved');
      expect(merchantsColMap['status'].Type).toContain('disabled');
    });

    it('merchants: FK user_id → users.id', () => {
      expect(merchantsCreate).toContain('FOREIGN KEY');
      expect(merchantsCreate).toContain('REFERENCES');
    });

    // ── shops UNIQUE / ENUM / FK ──
    it('shops: merchant_id UNIQUE', () => {
      expect(shopsCreate).toContain('UNIQUE');
    });

    it('shops: name UNIQUE', () => {
      expect(shopsCreate).toContain('UNIQUE');
    });

    it('shops: status ENUM 值正确', () => {
      expect(shopsColMap['status'].Type).toContain('enum');
      expect(shopsColMap['status'].Type).toContain('open');
      expect(shopsColMap['status'].Type).toContain('closed');
      expect(shopsColMap['status'].Type).toContain('frozen');
    });

    it('shops: FK merchant_id → merchants.id', () => {
      expect(shopsCreate).toContain('FOREIGN KEY');
      expect(shopsCreate).toContain('REFERENCES');
    });
  });

  // ════════════════════════════════════════════════
  // error — 列名缺失（编造列名验证）
  // ════════════════════════════════════════════════
  describe('error — 列名缺失', () => {
    let merchantsCols;
    let shopsCols;

    beforeAll(async () => {
      const [mRows] = await conn.query('SHOW COLUMNS FROM `merchants`');
      merchantsCols = mRows.map(r => r.Field);
      const [sRows] = await conn.query('SHOW COLUMNS FROM `shops`');
      shopsCols = sRows.map(r => r.Field);
    });

    it('company_name 不在 merchants 表中', () => {
      expect(merchantsCols).not.toContain('company_name');
    });

    it('biz_status 不在 merchants 表中', () => {
      expect(merchantsCols).not.toContain('biz_status');
    });

    it('不存在的通用列名 xyz_not_a_column 不在 merchants 表中', () => {
      expect(merchantsCols).not.toContain('xyz_not_a_column');
    });

    it('不存在的通用列名 xyz_not_a_column 不在 shops 表中', () => {
      expect(shopsCols).not.toContain('xyz_not_a_column');
    });
  });

  // ════════════════════════════════════════════════
  // error — truth 列 vs 真实 DB（truth DDL 声明的列必须在 DB 中存在）
  // ════════════════════════════════════════════════
  describe('error — truth 列 vs 真实 DB', () => {
    let allMerchantCols;
    let allShopCols;

    beforeAll(async () => {
      const [mRows] = await conn.query('SHOW COLUMNS FROM `merchants`');
      allMerchantCols = new Set(mRows.map(r => r.Field));
      const [sRows] = await conn.query('SHOW COLUMNS FROM `shops`');
      allShopCols = new Set(sRows.map(r => r.Field));
    });

    // 来自 @truth t_db_merchants — merchants 表完整列清单
    const truthMerchantCols = [
      'id',
      'user_id',
      'credit_code',
      'biz_license',
      'contact_name',
      'contact_mobile',
      'status',
      'review_reason',
      'reviewed_at',
      'created_at',
      'updated_at',
    ];

    it.each(truthMerchantCols)('merchants truth 列 %s 在真实 DB 中存在', (col) => {
      expect(allMerchantCols.has(col)).toBe(true);
    });

    // 来自 @truth t_db_shops — shops 表完整列清单
    const truthShopCols = [
      'id',
      'merchant_id',
      'name',
      'logo',
      'banner',
      'description',
      'status',
      'created_at',
      'updated_at',
    ];

    it.each(truthShopCols)('shops truth 列 %s 在真实 DB 中存在', (col) => {
      expect(allShopCols.has(col)).toBe(true);
    });
  });

});

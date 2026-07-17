/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_wallet', () => {
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

  // ════════════════════════════════════════════════════════════
  // correct — merchant_wallets 列名存在
  // ════════════════════════════════════════════════════════════
  describe('correct — merchant_wallets 列名存在 (getWallet / updateWalletBalance / createWallet)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `merchant_wallets`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 merchant_wallets 中存在', () => {
      expect(columns).toContain('id');
    });
    it('列 merchant_id 在 merchant_wallets 中存在', () => {
      expect(columns).toContain('merchant_id');
    });
    it('列 balance 在 merchant_wallets 中存在', () => {
      expect(columns).toContain('balance');
    });
    it('列 frozen_balance 在 merchant_wallets 中存在', () => {
      expect(columns).toContain('frozen_balance');
    });
    it('列 total_earned 在 merchant_wallets 中存在', () => {
      expect(columns).toContain('total_earned');
    });
    it('列 version 在 merchant_wallets 中存在', () => {
      expect(columns).toContain('version');
    });
    it('列 created_at 在 merchant_wallets 中存在', () => {
      expect(columns).toContain('created_at');
    });
    it('列 updated_at 在 merchant_wallets 中存在', () => {
      expect(columns).toContain('updated_at');
    });
  });

  // ════════════════════════════════════════════════════════════
  // correct — withdrawal_requests 列名存在
  // ════════════════════════════════════════════════════════════
  describe('correct — withdrawal_requests 列名存在 (createWithdrawal / getWithdrawalsByMerchant / updateWithdrawalStatus)', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `withdrawal_requests`');
      columns = rows.map(r => r.Field);
    });

    it('列 id 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('id');
    });
    it('列 request_no 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('request_no');
    });
    it('列 merchant_id 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('merchant_id');
    });
    it('列 amount 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('amount');
    });
    it('列 bank_account 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('bank_account');
    });
    it('列 status 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('status');
    });
    it('列 review_reason 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('review_reason');
    });
    it('列 paid_at 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('paid_at');
    });
    it('列 created_at 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('created_at');
    });
    it('列 updated_at 在 withdrawal_requests 中存在', () => {
      expect(columns).toContain('updated_at');
    });
  });

  // ════════════════════════════════════════════════════════════
  // boundary — merchant_wallets 约束 (NOT NULL / PK / AUTO_INC / UNIQUE / DEFAULT / DECIMAL)
  // ════════════════════════════════════════════════════════════
  describe('boundary — merchant_wallets 约束', () => {
    let colMap;
    let createTable;
    beforeAll(async () => {
      const [colRows] = await conn.query('SHOW COLUMNS FROM `merchant_wallets`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });
      const [ctRows] = await conn.query('SHOW CREATE TABLE `merchant_wallets`');
      createTable = ctRows[0]['Create Table'];
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    // NOT NULL — 全部列均为 NOT NULL (DDL: nullable=false)
    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('merchant_id 为 NOT NULL', () => { expect(colMap['merchant_id'].Null).toBe('NO'); });
    it('balance 为 NOT NULL', () => { expect(colMap['balance'].Null).toBe('NO'); });
    it('frozen_balance 为 NOT NULL', () => { expect(colMap['frozen_balance'].Null).toBe('NO'); });
    it('total_earned 为 NOT NULL', () => { expect(colMap['total_earned'].Null).toBe('NO'); });
    it('version 为 NOT NULL', () => { expect(colMap['version'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    // DEFAULT 值
    it('balance DEFAULT 0.00', () => { expect(colMap['balance'].Default).toBe('0.00'); });
    it('frozen_balance DEFAULT 0.00', () => { expect(colMap['frozen_balance'].Default).toBe('0.00'); });
    it('total_earned DEFAULT 0.00', () => { expect(colMap['total_earned'].Default).toBe('0.00'); });
    it('version DEFAULT 0', () => { expect(colMap['version'].Default).toBe('0'); });

    // DECIMAL(10,2) 类型
    it('balance 类型为 DECIMAL', () => { expect(colMap['balance'].Type).toContain('decimal'); });
    it('frozen_balance 类型为 DECIMAL', () => { expect(colMap['frozen_balance'].Type).toContain('decimal'); });
    it('total_earned 类型为 DECIMAL', () => { expect(colMap['total_earned'].Type).toContain('decimal'); });

    // UNIQUE on merchant_id
    it('merchant_id UNIQUE 约束存在', () => {
      expect(createTable).toContain('UNIQUE');
    });

    // FK
    it('merchant_wallets FK 约束存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ════════════════════════════════════════════════════════════
  // boundary — withdrawal_requests 约束 (NOT NULL / PK / AUTO_INC / UNIQUE / ENUM / DEFAULT / NULL)
  // ════════════════════════════════════════════════════════════
  describe('boundary — withdrawal_requests 约束', () => {
    let colMap;
    let createTable;
    beforeAll(async () => {
      const [colRows] = await conn.query('SHOW COLUMNS FROM `withdrawal_requests`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });
      const [ctRows] = await conn.query('SHOW CREATE TABLE `withdrawal_requests`');
      createTable = ctRows[0]['Create Table'];
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    // NOT NULL 列
    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('request_no 为 NOT NULL', () => { expect(colMap['request_no'].Null).toBe('NO'); });
    it('merchant_id 为 NOT NULL', () => { expect(colMap['merchant_id'].Null).toBe('NO'); });
    it('amount 为 NOT NULL', () => { expect(colMap['amount'].Null).toBe('NO'); });
    it('bank_account 为 NOT NULL', () => { expect(colMap['bank_account'].Null).toBe('NO'); });
    it('status 为 NOT NULL', () => { expect(colMap['status'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    // NULL 列
    it('review_reason 可为 NULL', () => { expect(colMap['review_reason'].Null).toBe('YES'); });
    it('paid_at 可为 NULL', () => { expect(colMap['paid_at'].Null).toBe('YES'); });

    // ENUM status
    it('status 为 ENUM 类型', () => { expect(colMap['status'].Type).toContain('enum'); });
    it('status ENUM 包含 pending', () => { expect(colMap['status'].Type).toContain('pending'); });
    it('status ENUM 包含 approved', () => { expect(colMap['status'].Type).toContain('approved'); });
    it('status ENUM 包含 paid', () => { expect(colMap['status'].Type).toContain('paid'); });
    it('status ENUM 包含 rejected', () => { expect(colMap['status'].Type).toContain('rejected'); });

    // DEFAULT
    it('status DEFAULT pending', () => { expect(colMap['status'].Default).toBe('pending'); });

    // UNIQUE on request_no
    it('request_no UNIQUE 约束存在', () => {
      expect(createTable).toContain('UNIQUE');
    });

    // FK
    it('withdrawal_requests FK 约束存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });
  });

  // ════════════════════════════════════════════════════════════
  // error — 编造列名 / 不存在的列
  // ════════════════════════════════════════════════════════════
  describe('error — 编造列名不存在', () => {
    let mwColumns;
    let wrColumns;
    beforeAll(async () => {
      const [mwRows] = await conn.query('SHOW COLUMNS FROM `merchant_wallets`');
      mwColumns = mwRows.map(r => r.Field);
      const [wrRows] = await conn.query('SHOW COLUMNS FROM `withdrawal_requests`');
      wrColumns = wrRows.map(r => r.Field);
    });

    it('wallet_balance 不在 merchant_wallets 中 (DDL 使用 balance)', () => {
      expect(mwColumns).not.toContain('wallet_balance');
    });

    it('不存在的列名 xyz_not_a_column 不在 merchant_wallets 中', () => {
      expect(mwColumns).not.toContain('xyz_not_a_column');
    });

    it('不存在的列名 xyz_not_a_column 不在 withdrawal_requests 中', () => {
      expect(wrColumns).not.toContain('xyz_not_a_column');
    });
  });

  // ════════════════════════════════════════════════════════════
  // error — service 源码表引用检查
  // ════════════════════════════════════════════════════════════
  describe('error — service 源码表引用检查', () => {
    it('merchantWalletService.js 引用 merchant_wallets 表', () => {
      const content = fs.readFileSync(path.join(workspace, 'services/merchantWalletService.js'), 'utf8');
      expect(content).toContain('merchant_wallets');
    });

    it('merchantWithdrawalService.js 引用 withdrawal_requests 表', () => {
      const content = fs.readFileSync(path.join(workspace, 'services/merchantWithdrawalService.js'), 'utf8');
      expect(content).toContain('withdrawal_requests');
    });
  });
});

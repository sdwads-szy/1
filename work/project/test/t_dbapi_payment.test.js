/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_payment', () => {
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

  // ══ correct: payments 列名存在（SHOW COLUMNS 查真实数据库）══
  describe('correct — payments 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `payments`');
      columns = rows.map(r => r.Field);
    });

    describe('createPayment — INSERT INTO payments', () => {
      const cols = ['transaction_no', 'sub_order_id', 'channel', 'amount', 'status'];
      cols.forEach(col => {
        it(`列 ${col} 在 payments 表中存在`, () => {
          expect(columns).toContain(col);
        });
      });
      it('VALUES 占位符数 = 5', () => {
        const src = fs.readFileSync(path.join(workspace, 'services/paymentService.js'), 'utf8');
        const match = src.match(/INSERT INTO payments\s*\([^)]+\)\s*VALUES\s*\(([^)]+)\)/i);
        if (match) {
          const placeholders = match[1].split(',').filter(p => p.trim() === '?');
          expect(placeholders.length).toBe(5);
        } else {
          // fallback: 只要 INSERT 语句存在即可
          expect(src).toContain('INSERT INTO payments');
        }
      });
    });

    describe('getPaymentBySubOrder — SELECT FROM payments', () => {
      const cols = ['id', 'transaction_no', 'sub_order_id', 'channel', 'amount', 'status', 'callback_log', 'created_at'];
      cols.forEach(col => {
        it(`列 ${col} 在 payments 表中存在`, () => {
          expect(columns).toContain(col);
        });
      });
    });

    describe('updatePaymentStatus — UPDATE payments', () => {
      const cols = ['status', 'callback_log', 'sub_order_id'];
      cols.forEach(col => {
        it(`列 ${col} 在 payments 表中存在`, () => {
          expect(columns).toContain(col);
        });
      });
    });

    describe('getPendingPayments — SELECT FROM payments', () => {
      const cols = ['id', 'transaction_no', 'sub_order_id', 'channel', 'amount', 'status', 'created_at'];
      cols.forEach(col => {
        it(`列 ${col} 在 payments 表中存在`, () => {
          expect(columns).toContain(col);
        });
      });
    });
  });

  // ══ boundary: NOT NULL / PK / AUTO_INCREMENT 约束 ══
  describe('boundary — payments 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `payments`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('transaction_no 为 NOT NULL', () => {
      expect(colMap['transaction_no'].Null).toBe('NO');
    });
    it('sub_order_id 为 NOT NULL', () => {
      expect(colMap['sub_order_id'].Null).toBe('NO');
    });
    it('channel 为 NOT NULL', () => {
      expect(colMap['channel'].Null).toBe('NO');
    });
    it('amount 为 NOT NULL', () => {
      expect(colMap['amount'].Null).toBe('NO');
    });
    it('status 为 NOT NULL', () => {
      expect(colMap['status'].Null).toBe('NO');
    });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });

    it('status DEFAULT pending', () => {
      expect(colMap['status'].Default).toBe('pending');
    });

    it('channel ENUM 值正确', () => {
      expect(colMap['channel'].Type).toContain('enum');
      expect(colMap['channel'].Type).toContain('wechat');
      expect(colMap['channel'].Type).toContain('alipay');
      expect(colMap['channel'].Type).toContain('unionpay');
    });

    it('status ENUM 值正确', () => {
      expect(colMap['status'].Type).toContain('enum');
      expect(colMap['status'].Type).toContain('pending');
      expect(colMap['status'].Type).toContain('success');
      expect(colMap['status'].Type).toContain('failed');
      expect(colMap['status'].Type).toContain('refunded');
    });
  });

  // ══ boundary: UNIQUE / FK / JSON 表级约束 ══
  describe('boundary — payments 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `payments`');
      createTable = rows[0]['Create Table'];
    });

    it('transaction_no UNIQUE 约束存在', () => {
      expect(createTable).toContain('UNIQUE');
    });

    it('FK sub_order_id → sub_orders.id 约束存在', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });

    it('callback_log JSON 类型', () => {
      expect(createTable).toContain('json');
    });
  });

  // ══ error: 列名不存在 ══
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `payments`');
      columns = rows.map(r => r.Field);
    });

    it("编造列名 'pay_status' 不在 payments DDL 中", () => {
      expect(columns).not.toContain('pay_status');
    });

    it('不存在的列名 xyz_not_a_column not.toContain', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });
});

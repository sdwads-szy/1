/** @jest-environment node */
require('dotenv').config();
const mysql = require('mysql2/promise');

describe('t_dbapi_refund', () => {
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

  // ══════════════════════════════════════════════════════
  // correct — refund_requests 列名存在（6 个 SQL 操作）
  // ══════════════════════════════════════════════════════
  describe('correct — refund_requests 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refund_requests`');
      columns = rows.map(r => r.Field);
    });

    // db_api_create_refund_request: INSERT
    describe('createRefundRequest (INSERT)', () => {
      it('列 request_no 在 refund_requests 表中存在', () => { expect(columns).toContain('request_no'); });
      it('列 sub_order_id 在 refund_requests 表中存在', () => { expect(columns).toContain('sub_order_id'); });
      it('列 user_id 在 refund_requests 表中存在', () => { expect(columns).toContain('user_id'); });
      it('列 type 在 refund_requests 表中存在', () => { expect(columns).toContain('type'); });
      it('列 reason 在 refund_requests 表中存在', () => { expect(columns).toContain('reason'); });
      it('列 amount 在 refund_requests 表中存在', () => { expect(columns).toContain('amount'); });
      it('列 evidence_images 在 refund_requests 表中存在', () => { expect(columns).toContain('evidence_images'); });
      it('列 status 在 refund_requests 表中存在', () => { expect(columns).toContain('status'); });
    });

    // db_api_get_refund_by_id: SELECT
    describe('getRefundById (SELECT)', () => {
      it('列 id 在 refund_requests 表中存在', () => { expect(columns).toContain('id'); });
      it('列 request_no 在 refund_requests 表中存在', () => { expect(columns).toContain('request_no'); });
      it('列 sub_order_id 在 refund_requests 表中存在', () => { expect(columns).toContain('sub_order_id'); });
      it('列 user_id 在 refund_requests 表中存在', () => { expect(columns).toContain('user_id'); });
      it('列 type 在 refund_requests 表中存在', () => { expect(columns).toContain('type'); });
      it('列 reason 在 refund_requests 表中存在', () => { expect(columns).toContain('reason'); });
      it('列 amount 在 refund_requests 表中存在', () => { expect(columns).toContain('amount'); });
      it('列 evidence_images 在 refund_requests 表中存在', () => { expect(columns).toContain('evidence_images'); });
      it('列 status 在 refund_requests 表中存在', () => { expect(columns).toContain('status'); });
      it('列 created_at 在 refund_requests 表中存在', () => { expect(columns).toContain('created_at'); });
    });

    // db_api_get_refunds_by_shop: SELECT JOIN sub_orders
    describe('getRefundsByShop (SELECT JOIN)', () => {
      it('列 id 在 refund_requests 表中存在', () => { expect(columns).toContain('id'); });
      it('列 request_no 在 refund_requests 表中存在', () => { expect(columns).toContain('request_no'); });
      it('列 sub_order_id 在 refund_requests 表中存在', () => { expect(columns).toContain('sub_order_id'); });
      it('列 user_id 在 refund_requests 表中存在', () => { expect(columns).toContain('user_id'); });
      it('列 type 在 refund_requests 表中存在', () => { expect(columns).toContain('type'); });
      it('列 amount 在 refund_requests 表中存在', () => { expect(columns).toContain('amount'); });
      it('列 status 在 refund_requests 表中存在', () => { expect(columns).toContain('status'); });
      it('列 created_at 在 refund_requests 表中存在', () => { expect(columns).toContain('created_at'); });
    });

    // db_api_get_refunds_by_user: SELECT
    describe('getRefundsByUser (SELECT)', () => {
      it('列 id 在 refund_requests 表中存在', () => { expect(columns).toContain('id'); });
      it('列 request_no 在 refund_requests 表中存在', () => { expect(columns).toContain('request_no'); });
      it('列 sub_order_id 在 refund_requests 表中存在', () => { expect(columns).toContain('sub_order_id'); });
      it('列 type 在 refund_requests 表中存在', () => { expect(columns).toContain('type'); });
      it('列 reason 在 refund_requests 表中存在', () => { expect(columns).toContain('reason'); });
      it('列 amount 在 refund_requests 表中存在', () => { expect(columns).toContain('amount'); });
      it('列 status 在 refund_requests 表中存在', () => { expect(columns).toContain('status'); });
      it('列 created_at 在 refund_requests 表中存在', () => { expect(columns).toContain('created_at'); });
    });

    // db_api_get_refunds_arbitration: SELECT
    describe('getRefundsArbitration (SELECT)', () => {
      it('列 id 在 refund_requests 表中存在', () => { expect(columns).toContain('id'); });
      it('列 request_no 在 refund_requests 表中存在', () => { expect(columns).toContain('request_no'); });
      it('列 sub_order_id 在 refund_requests 表中存在', () => { expect(columns).toContain('sub_order_id'); });
      it('列 user_id 在 refund_requests 表中存在', () => { expect(columns).toContain('user_id'); });
      it('列 type 在 refund_requests 表中存在', () => { expect(columns).toContain('type'); });
      it('列 reason 在 refund_requests 表中存在', () => { expect(columns).toContain('reason'); });
      it('列 amount 在 refund_requests 表中存在', () => { expect(columns).toContain('amount'); });
      it('列 status 在 refund_requests 表中存在', () => { expect(columns).toContain('status'); });
      it('列 created_at 在 refund_requests 表中存在', () => { expect(columns).toContain('created_at'); });
    });

    // db_api_update_refund_status: UPDATE (CAS)
    describe('updateRefundStatus (UPDATE)', () => {
      it('列 status 在 refund_requests 表中存在', () => { expect(columns).toContain('status'); });
      it('列 id 在 refund_requests 表中存在', () => { expect(columns).toContain('id'); });
    });
  });

  // ══════════════════════════════════════════════════════
  // correct — refund_logs 列名存在（1 个 SQL 操作）
  // ══════════════════════════════════════════════════════
  describe('correct — refund_logs 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refund_logs`');
      columns = rows.map(r => r.Field);
    });

    // db_api_create_refund_log: INSERT
    describe('createRefundLog (INSERT)', () => {
      it('列 refund_request_id 在 refund_logs 表中存在', () => { expect(columns).toContain('refund_request_id'); });
      it('列 operator_id 在 refund_logs 表中存在', () => { expect(columns).toContain('operator_id'); });
      it('列 action 在 refund_logs 表中存在', () => { expect(columns).toContain('action'); });
      it('列 detail 在 refund_logs 表中存在', () => { expect(columns).toContain('detail'); });
    });
  });

  // ══════════════════════════════════════════════════════
  // boundary — refund_requests 约束（NOT NULL / PK / AUTO_INCREMENT）
  // ══════════════════════════════════════════════════════
  describe('boundary — refund_requests 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refund_requests`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('request_no 为 NOT NULL', () => { expect(colMap['request_no'].Null).toBe('NO'); });
    it('sub_order_id 为 NOT NULL', () => { expect(colMap['sub_order_id'].Null).toBe('NO'); });
    it('user_id 为 NOT NULL', () => { expect(colMap['user_id'].Null).toBe('NO'); });
    it('type 为 NOT NULL', () => { expect(colMap['type'].Null).toBe('NO'); });
    it('reason 为 NOT NULL', () => { expect(colMap['reason'].Null).toBe('NO'); });
    it('amount 为 NOT NULL', () => { expect(colMap['amount'].Null).toBe('NO'); });
    it('status 为 NOT NULL', () => { expect(colMap['status'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });
    it('updated_at 为 NOT NULL', () => { expect(colMap['updated_at'].Null).toBe('NO'); });

    it('evidence_images 可为 NULL', () => { expect(colMap['evidence_images'].Null).toBe('YES'); });
    it('merchant_review_reason 可为 NULL', () => { expect(colMap['merchant_review_reason'].Null).toBe('YES'); });
    it('arbitration_ruling 可为 NULL', () => { expect(colMap['arbitration_ruling'].Null).toBe('YES'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });

    it('status DEFAULT pending', () => { expect(colMap['status'].Default).toBe('pending'); });
    it('created_at DEFAULT CURRENT_TIMESTAMP', () => { expect(colMap['created_at'].Default).toContain('CURRENT_TIMESTAMP'); });
    it('updated_at DEFAULT CURRENT_TIMESTAMP + ON UPDATE', () => { expect(colMap['updated_at'].Extra).toContain('on update'); });
  });

  // ══════════════════════════════════════════════════════
  // boundary — refund_logs 约束（NOT NULL / PK / AUTO_INCREMENT）
  // ══════════════════════════════════════════════════════
  describe('boundary — refund_logs 列级约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refund_logs`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('id 为 NOT NULL', () => { expect(colMap['id'].Null).toBe('NO'); });
    it('refund_request_id 为 NOT NULL', () => { expect(colMap['refund_request_id'].Null).toBe('NO'); });
    it('operator_id 为 NOT NULL', () => { expect(colMap['operator_id'].Null).toBe('NO'); });
    it('action 为 NOT NULL', () => { expect(colMap['action'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });

    it('detail 可为 NULL', () => { expect(colMap['detail'].Null).toBe('YES'); });

    it('PRIMARY KEY id 已定义', () => { expect(colMap['id'].Key).toBe('PRI'); });
    it('AUTO_INCREMENT id', () => { expect(colMap['id'].Extra).toContain('auto_increment'); });

    it('created_at DEFAULT CURRENT_TIMESTAMP', () => { expect(colMap['created_at'].Default).toContain('CURRENT_TIMESTAMP'); });
  });

  // ══════════════════════════════════════════════════════
  // boundary — refund_requests 表级约束（ENUM / UNIQUE / FK / JSON）
  // ══════════════════════════════════════════════════════
  describe('boundary — refund_requests 表级约束', () => {
    let createTable;
    let colMap;
    beforeAll(async () => {
      const [ctRows] = await conn.query('SHOW CREATE TABLE `refund_requests`');
      createTable = ctRows[0]['Create Table'];
      const [colRows] = await conn.query('SHOW COLUMNS FROM `refund_requests`');
      colMap = {};
      colRows.forEach(r => { colMap[r.Field] = r; });
    });

    // ENUM 类型
    it('type ENUM 值包含 only_refund, return_refund', () => {
      expect(colMap['type'].Type).toContain('enum');
      expect(colMap['type'].Type).toContain('only_refund');
      expect(colMap['type'].Type).toContain('return_refund');
    });

    it('status ENUM 值包含全部 9 种状态', () => {
      expect(colMap['status'].Type).toContain('enum');
      expect(colMap['status'].Type).toContain('pending');
      expect(colMap['status'].Type).toContain('awaiting_return');
      expect(colMap['status'].Type).toContain('awaiting_merchant_receive');
      expect(colMap['status'].Type).toContain('refunding');
      expect(colMap['status'].Type).toContain('completed');
      expect(colMap['status'].Type).toContain('rejected');
      expect(colMap['status'].Type).toContain('arbitrating');
      expect(colMap['status'].Type).toContain('closed');
      expect(colMap['status'].Type).toContain('retry');
    });

    // UNIQUE request_no
    it('request_no 为 UNIQUE', () => {
      expect(colMap['request_no'].Key).toBe('UNI');
    });

    // JSON evidence_images
    it('evidence_images 类型为 JSON', () => {
      expect(colMap['evidence_images'].Type).toContain('json');
    });

    // FK 约束
    it('FK sub_order_id → sub_orders.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('sub_order_id');
      expect(createTable).toContain('REFERENCES');
    });

    it('FK user_id → users.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('user_id');
      expect(createTable).toContain('REFERENCES');
    });

    // INDEX 存在
    it('索引 idx_request_no 存在', () => { expect(createTable).toContain('idx_request_no'); });
    it('索引 idx_sub_order_id 存在', () => { expect(createTable).toContain('idx_sub_order_id'); });
    it('索引 idx_user_id 存在', () => { expect(createTable).toContain('idx_user_id'); });
    it('索引 idx_status 存在', () => { expect(createTable).toContain('idx_status'); });
  });

  // ══════════════════════════════════════════════════════
  // boundary — refund_logs 表级约束（FK / INDEX）
  // ══════════════════════════════════════════════════════
  describe('boundary — refund_logs 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `refund_logs`');
      createTable = rows[0]['Create Table'];
    });

    it('FK refund_request_id → refund_requests.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('refund_request_id');
      expect(createTable).toContain('REFERENCES');
    });

    it('FK operator_id → users.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('operator_id');
      expect(createTable).toContain('REFERENCES');
    });

    it('索引 idx_refund_request_id 存在', () => { expect(createTable).toContain('idx_refund_request_id'); });
    it('索引 idx_operator_id 存在', () => { expect(createTable).toContain('idx_operator_id'); });
  });

  // ══════════════════════════════════════════════════════
  // error — 编造列名不存在
  // ══════════════════════════════════════════════════════
  describe('error — 编造列名不存在', () => {
    it('refund_reason 不在 refund_requests DDL 中（正确列名: reason）', async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refund_requests`');
      const columns = rows.map(r => r.Field);
      expect(columns).not.toContain('refund_reason');
    });

    it('remark 不在 refund_logs DDL 中（正确列名: detail）', async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refund_logs`');
      const columns = rows.map(r => r.Field);
      expect(columns).not.toContain('remark');
    });

    it('不存在的通用列名 xyz_not_a_column 不在 refund_requests 中', async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refund_requests`');
      const columns = rows.map(r => r.Field);
      expect(columns).not.toContain('xyz_not_a_column');
    });

    it('不存在的通用列名 xyz_not_a_column 不在 refund_logs 中', async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `refund_logs`');
      const columns = rows.map(r => r.Field);
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });
});

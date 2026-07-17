/** @jest-environment node */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const workspace = path.resolve(__dirname, '..');

describe('t_dbapi_operation_log', () => {
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

  // ══ correct: INSERT INTO operation_logs — 列名对齐（含 detail JSON）══
  describe('correct — operation_logs 列名存在', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `operation_logs`');
      columns = rows.map(r => r.Field);
    });

    it('admin_id 列存在', () => { expect(columns).toContain('admin_id'); });
    it('action 列存在', () => { expect(columns).toContain('action'); });
    it('target_type 列存在', () => { expect(columns).toContain('target_type'); });
    it('target_id 列存在', () => { expect(columns).toContain('target_id'); });
    it('detail 列存在', () => { expect(columns).toContain('detail'); });
    it('created_at 列存在', () => { expect(columns).toContain('created_at'); });
  });

  // ══ boundary: NOT NULL / PK / AUTO_INCREMENT ══
  describe('boundary — operation_logs 约束', () => {
    let colMap;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `operation_logs`');
      colMap = {};
      rows.forEach(r => { colMap[r.Field] = r; });
    });

    it('admin_id 为 NOT NULL', () => { expect(colMap['admin_id'].Null).toBe('NO'); });
    it('action 为 NOT NULL', () => { expect(colMap['action'].Null).toBe('NO'); });
    it('target_type 为 NOT NULL', () => { expect(colMap['target_type'].Null).toBe('NO'); });
    it('target_id 为 NOT NULL', () => { expect(colMap['target_id'].Null).toBe('NO'); });
    it('created_at 为 NOT NULL', () => { expect(colMap['created_at'].Null).toBe('NO'); });

    it('PRIMARY KEY id 已定义', () => {
      expect(colMap['id'].Key).toBe('PRI');
    });

    it('AUTO_INCREMENT id', () => {
      expect(colMap['id'].Extra).toContain('auto_increment');
    });
  });

  // ══ boundary: FK + 复合索引 + JSON ══
  describe('boundary — operation_logs 表级约束', () => {
    let createTable;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW CREATE TABLE `operation_logs`');
      createTable = rows[0]['Create Table'];
    });

    it('FK admin_id → users.id', () => {
      expect(createTable).toContain('FOREIGN KEY');
      expect(createTable).toContain('REFERENCES');
    });

    it('复合索引 idx_target (target_type, target_id)', () => {
      expect(createTable).toContain('idx_target');
    });

    it('索引 idx_created_at', () => {
      expect(createTable).toContain('idx_created_at');
    });

    it('索引 idx_admin_id', () => {
      expect(createTable).toContain('idx_admin_id');
    });
  });

  // ══ error: 编造列名 operator_id 不在 operation_logs DDL 中 ══
  describe('error — 列名缺失', () => {
    let columns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `operation_logs`');
      columns = rows.map(r => r.Field);
    });

    it('operator_id 不在 operation_logs 中（DDL 使用 admin_id）', () => {
      expect(columns).not.toContain('operator_id');
    });

    it('不存在的列名 xyz_not_a_column 不在表中', () => {
      expect(columns).not.toContain('xyz_not_a_column');
    });
  });

  // ══ error: truth DDL 列 vs 真实 DB 对齐 ══
  describe('error — truth 列 vs 真实 DB', () => {
    let allColumns;
    beforeAll(async () => {
      const [rows] = await conn.query('SHOW COLUMNS FROM `operation_logs`');
      allColumns = new Set(rows.map(r => r.Field));
    });

    it('operation_logs.admin_id 在 DB 中存在', () => {
      expect(allColumns.has('admin_id')).toBe(true);
    });
    it('operation_logs.action 在 DB 中存在', () => {
      expect(allColumns.has('action')).toBe(true);
    });
    it('operation_logs.target_type 在 DB 中存在', () => {
      expect(allColumns.has('target_type')).toBe(true);
    });
    it('operation_logs.target_id 在 DB 中存在', () => {
      expect(allColumns.has('target_id')).toBe(true);
    });
    it('operation_logs.detail 在 DB 中存在', () => {
      expect(allColumns.has('detail')).toBe(true);
    });
    it('operation_logs.created_at 在 DB 中存在', () => {
      expect(allColumns.has('created_at')).toBe(true);
    });
  });
});

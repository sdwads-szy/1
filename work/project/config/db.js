const mysql = require('mysql2/promise');
require('dotenv').config();

const pool = mysql.createPool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT) || 3306,
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'testdb',
  waitForConnections: true,
  connectionLimit: 20,
  maxIdle: 5,
  idleTimeout: 60000,
  queueLimit: 0,
  enableKeepAlive: true,
  keepAliveInitialDelay: 0,
});

/**
 * 执行 SQL 查询（已解构 pool.execute，返回 rows 数组）
 * @param {string} sql - SQL 语句
 * @param {Array} params - 参数化值
 * @returns {Promise<Array>} rows - 结果行数组；写操作返回 ResultSetHeader
 */
async function query(sql, params) {
  const [rows] = await pool.execute(sql, params);
  return rows;
}

/**
 * 测试数据库连接
 * @returns {Promise<boolean>}
 */
async function testConnection() {
  const [rows] = await pool.execute('SELECT 1');
  return rows !== undefined;
}

/**
 * 开启事务 — 每个事务独立获取连接，禁止模块级变量
 * @returns {Promise<PoolConnection>} conn - 事务连接对象
 */
async function beginTransaction() {
  const conn = await pool.getConnection();
  await conn.beginTransaction();
  return conn;
}

/**
 * 提交事务并释放连接
 * @param {PoolConnection} conn
 */
async function commit(conn) {
  await conn.commit();
  conn.release();
}

/**
 * 回滚事务并释放连接
 * @param {PoolConnection} conn
 */
async function rollback(conn) {
  await conn.rollback();
  conn.release();
}

module.exports = { pool, query, beginTransaction, commit, rollback, testConnection };

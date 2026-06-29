/**
 * MySQL 数据库连接配置
 * 使用 mysql2/promise 连接池，提供事务支持
 */
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT) || 3306,
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'testdb',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
  enableKeepAlive: true,
  keepAliveInitialDelay: 0
});

/**
 * 执行 SQL 查询（已解构 pool.execute，调用方禁止再解构返回值）
 * @param {string} sql - SQL 语句，使用 ? 占位符
 * @param {Array} params - 参数数组
 * @returns {Promise<Array|ResultSetHeader>} SELECT 返回行数组，写操作返回 ResultSetHeader
 */
async function query(sql, params = []) {
  const [rows] = await pool.execute(sql, params);
  return rows;
}

/**
 * 开启事务，每个事务独立获取连接（禁止模块级共享连接变量）
 * @returns {Promise<mysql.PoolConnection>} 事务连接对象
 */
async function beginTransaction() {
  const conn = await pool.getConnection();
  await conn.beginTransaction();
  return conn;
}

/**
 * 提交事务并释放连接
 * @param {mysql.PoolConnection} conn - 事务连接
 */
async function commit(conn) {
  await conn.commit();
  conn.release();
}

/**
 * 回滚事务并释放连接
 * @param {mysql.PoolConnection} conn - 事务连接
 */
async function rollback(conn) {
  await conn.rollback();
  conn.release();
}

/**
 * 测试数据库连接是否正常
 * @returns {Promise<boolean>}
 */
async function testConnection() {
  try {
    await pool.execute('SELECT 1');
    return true;
  } catch {
    return false;
  }
}

module.exports = { pool, query, beginTransaction, commit, rollback, testConnection };

/**
 * 数据库初始化脚本
 * 用法: node scripts/init-db.js
 * 功能: 创建数据库（如不存在），读取 database/ 目录下所有 .sql 文件并按文件名排序执行
 */

require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });

const mysql = require('mysql2/promise');
const fs = require('fs');
const path = require('path');
const db = require('../config/db');
const logger = require('../config/logger');

const DB_NAME = process.env.DB_NAME || 'testdb';
const SQL_DIR = path.join(__dirname, '..', 'database');

/**
 * 创建数据库（如不存在）
 * 使用独立连接，因为连接池依赖数据库已存在
 */
async function ensureDatabase() {
  const conn = await mysql.createConnection({
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT) || 3306,
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
  });

  try {
    await conn.query(
      `CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`
    );
    logger.info(`Database '${DB_NAME}' ensured.`);
  } finally {
    await conn.end();
  }
}

/**
 * 读取并解析 SQL 文件，按 ; 拆分为独立语句并过滤空语句
 * @param {string} filePath - SQL 文件绝对路径
 * @returns {string[]} 非空 SQL 语句数组
 */
function parseSQLFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  return content
    .split(';')
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

/**
 * 按顺序执行 database/ 目录下的所有 .sql 文件
 */
async function executeSQLFiles() {
  if (!fs.existsSync(SQL_DIR)) {
    logger.warn(`SQL directory not found: ${SQL_DIR}, skipping DDL execution.`);
    return;
  }

  const files = fs
    .readdirSync(SQL_DIR)
    .filter((f) => f.endsWith('.sql'))
    .sort();

  if (files.length === 0) {
    logger.warn('No .sql files found in database/ directory.');
    return;
  }

  for (const file of files) {
    const filePath = path.join(SQL_DIR, file);
    const statements = parseSQLFile(filePath);

    for (const stmt of statements) {
      try {
        await db.query(stmt);
      } catch (err) {
        logger.error(`Failed executing statement from ${file}: ${stmt.substring(0, 80)}...`);
        throw err;
      }
    }

    logger.info(`Executed: ${file} (${statements.length} statements)`);
  }
}

/**
 * 主流程：确保数据库存在 → 执行 DDL → 验证连接
 */
async function initDB() {
  logger.info('Starting database initialization...');

  await ensureDatabase();
  await db.testConnection();
  await executeSQLFiles();

  logger.info('Database initialization completed successfully.');
  process.exit(0);
}

initDB().catch((err) => {
  logger.error(`Database initialization failed: ${err.message}`);
  process.exit(1);
});

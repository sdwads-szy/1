/**
 * 种子用户脚本
 * 用法: node scripts/seed-users.js
 * 功能: 创建默认管理员账号（如不存在），密码使用 bcrypt 哈希
 */

require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });

const bcrypt = require('bcrypt');
const db = require('../config/db');
const logger = require('../config/logger');

const SALT_ROUNDS = 10;

/** 默认管理员配置，可通过环境变量覆盖 */
const ADMIN_CONFIG = {
  username: process.env.ADMIN_USERNAME || 'admin',
  email: process.env.ADMIN_EMAIL || 'admin@example.com',
  password: process.env.ADMIN_PASSWORD || 'admin123',
  role: 'admin',
};

/**
 * 创建管理员用户
 * 先检查邮箱是否已存在，存在则跳过
 */
async function seedAdminUser() {
  const { username, email, password, role } = ADMIN_CONFIG;

  const existing = await db.query('SELECT id FROM users WHERE email = ?', [email]);
  if (existing.length > 0) {
    logger.info(`Admin user '${email}' already exists, skipping.`);
    return;
  }

  const hashedPassword = await bcrypt.hash(password, SALT_ROUNDS);

  const result = await db.query(
    'INSERT INTO users (username, email, password, role, created_at) VALUES (?, ?, ?, ?, NOW())',
    [username, email, hashedPassword, role]
  );

  logger.info(`Admin user created: ${email} (id=${result.insertId})`);
}

/**
 * 主流程
 */
async function seedUsers() {
  logger.info('Starting user seeding...');

  await db.testConnection();
  await seedAdminUser();

  logger.info('User seeding completed.');
  process.exit(0);
}

seedUsers().catch((err) => {
  logger.error(`User seeding failed: ${err.message}`);
  process.exit(1);
});

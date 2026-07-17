const crypto = require('crypto');
const bcrypt = require('bcryptjs');

const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'default-encryption-key-change-in-production';
const SALT_ROUNDS = 10;
const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 12;

function getKey() {
  return crypto.createHash('sha256').update(ENCRYPTION_KEY).digest();
}

const encryption = {
  /**
   * 使用 bcrypt 对密码进行哈希
   * @param {string} password - 明文密码
   * @returns {Promise<string>} bcrypt 哈希值
   */
  async hashPassword(password) {
    return bcrypt.hash(password, SALT_ROUNDS);
  },

  /**
   * 验证密码与哈希是否匹配
   * @param {string} password - 明文密码
   * @param {string} hash - bcrypt 哈希值
   * @returns {Promise<boolean>} 是否匹配
   */
  async comparePassword(password, hash) {
    return bcrypt.compare(password, hash);
  },

  /**
   * AES-256-GCM 加密敏感数据
   * @param {string} plaintext - 明文
   * @returns {string} 格式: base64(iv):base64(authTag):base64(ciphertext)
   */
  encrypt(plaintext) {
    const key = getKey();
    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
    let encrypted = cipher.update(String(plaintext), 'utf8', 'base64');
    encrypted += cipher.final('base64');
    const authTag = cipher.getAuthTag().toString('base64');
    return `${iv.toString('base64')}:${authTag}:${encrypted}`;
  },

  /**
   * AES-256-GCM 解密
   * @param {string} ciphertext - encrypt() 的输出
   * @returns {string} 明文
   * @throws {Error} 格式错误或认证失败
   */
  decrypt(ciphertext) {
    const key = getKey();
    const parts = String(ciphertext).split(':');
    if (parts.length !== 3) {
      throw new Error('Invalid ciphertext format');
    }
    const iv = Buffer.from(parts[0], 'base64');
    const authTag = Buffer.from(parts[1], 'base64');
    const encrypted = parts[2];
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(authTag);
    let decrypted = decipher.update(encrypted, 'base64', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  }
};

module.exports = encryption;

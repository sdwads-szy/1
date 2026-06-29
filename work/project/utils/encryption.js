const crypto = require('crypto');

const ALGORITHM = 'aes-256-cbc';
const IV_LENGTH = 16;

/**
 * Get the encryption key from env, padded/trimmed to 32 bytes.
 * @returns {Buffer}
 */
function getKey() {
  const raw = process.env.ENCRYPTION_KEY || 'your_encryption_key_32chars';
  return Buffer.from(raw.padEnd(32, '0').slice(0, 32), 'utf8');
}

/**
 * Encrypt plaintext using AES-256-CBC.
 * @param {string} text - Plain text to encrypt
 * @returns {string} Hex-encoded IV + ciphertext
 */
function encrypt(text) {
  const key = getKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return iv.toString('hex') + ':' + encrypted;
}

/**
 * Decrypt ciphertext produced by encrypt().
 * @param {string} text - Hex-encoded IV:ciphertext
 * @returns {string} Decrypted plain text
 */
function decrypt(text) {
  const key = getKey();
  const parts = text.split(':');
  const iv = Buffer.from(parts.shift(), 'hex');
  const encryptedText = parts.join(':');
  const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
  let decrypted = decipher.update(encryptedText, 'hex', 'utf8');
  decrypted += decipher.final('utf8');
  return decrypted;
}

/**
 * Hash a string using SHA-256 (one-way, for integrity checks).
 * @param {string} text
 * @returns {string} Hex digest
 */
function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

module.exports = { encrypt, decrypt, sha256 };

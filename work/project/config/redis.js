/**
 * Redis 连接配置与基础缓存工具
 * 使用 redis@4 客户端
 */
const redis = require('redis');

const client = redis.createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379/0'
});

client.on('error', (err) => {
  console.warn('Redis connection error:', err.message);
});

client.on('connect', () => {
  console.log('Redis connected');
});

// 启动连接（失败不阻塞进程）
client.connect().catch((err) => {
  console.warn('Redis initial connect failed:', err.message);
});

/**
 * 获取缓存值
 * @param {string} key
 * @returns {Promise<string|null>}
 */
async function get(key) {
  try {
    return await client.get(key);
  } catch {
    return null;
  }
}

/**
 * 设置缓存值（带过期时间）
 * @param {string} key
 * @param {*} value
 * @param {number} ttl - 过期秒数，默认 300
 */
async function set(key, value, ttl = 300) {
  try {
    await client.setEx(key, ttl, String(value));
  } catch {
    // 缓存写入失败静默忽略
  }
}

/**
 * 删除缓存
 * @param {string} key
 */
async function del(key) {
  try {
    await client.del(key);
  } catch {
    // 静默忽略
  }
}

/**
 * 自增
 * @param {string} key
 * @returns {Promise<number|null>}
 */
async function incr(key) {
  try {
    return await client.incr(key);
  } catch {
    return null;
  }
}

/**
 * 自减
 * @param {string} key
 * @returns {Promise<number|null>}
 */
async function decr(key) {
  try {
    return await client.decr(key);
  } catch {
    return null;
  }
}

/**
 * 获取哈希字段
 * @param {string} key
 * @param {string} field
 * @returns {Promise<string|null>}
 */
async function hget(key, field) {
  try {
    return await client.hGet(key, field);
  } catch {
    return null;
  }
}

/**
 * 设置哈希字段
 * @param {string} key
 * @param {string} field
 * @param {*} value
 */
async function hset(key, field, value) {
  try {
    await client.hSet(key, field, String(value));
  } catch {
    // 静默忽略
  }
}

/**
 * 设置过期时间
 * @param {string} key
 * @param {number} ttl - 过期秒数
 */
async function expire(key, ttl) {
  try {
    await client.expire(key, ttl);
  } catch {
    // 静默忽略
  }
}

module.exports = { client, get, set, del, incr, decr, hget, hset, expire };

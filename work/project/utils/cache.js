const Redis = require('ioredis');

const client = new Redis(process.env.REDIS_URL || 'redis://localhost:6379/0', {
  maxRetriesPerRequest: 3,
  retryStrategy(times) {
    if (times > 3) return null;
    return Math.min(times * 200, 2000);
  },
  lazyConnect: true
});

client.on('error', (err) => console.warn('Redis error:', err.message));

/** Lazy connect — does not block startup if Redis is unavailable */
client.connect().catch(() => {});

const cache = {
  /**
   * Get a cached value by key.
   * @param {string} key
   * @returns {Promise<string|null>}
   */
  async get(key) {
    try { return await client.get(key); } catch { return null; }
  },

  /**
   * Set a cached value with TTL.
   * @param {string} key
   * @param {*} value
   * @param {number} ttl - Seconds (default 300)
   */
  async set(key, value, ttl = 300) {
    try { await client.set(key, String(value), 'EX', ttl); } catch {}
  },

  /**
   * Delete a cached key.
   * @param {string} key
   */
  async del(key) {
    try { await client.del(key); } catch {}
  },

  /**
   * Increment a counter.
   * @param {string} key
   * @returns {Promise<number|null>}
   */
  async incr(key) {
    try { return await client.incr(key); } catch { return null; }
  },

  /**
   * Decrement a counter.
   * @param {string} key
   * @returns {Promise<number|null>}
   */
  async decr(key) {
    try { return await client.decr(key); } catch { return null; }
  },

  /**
   * Get a hash field.
   * @param {string} key
   * @param {string} field
   * @returns {Promise<string|null>}
   */
  async hget(key, field) {
    try { return await client.hget(key, field); } catch { return null; }
  },

  /**
   * Set a hash field.
   * @param {string} key
   * @param {string} field
   * @param {*} value
   */
  async hset(key, field, value) {
    try { await client.hset(key, field, String(value)); } catch {}
  },

  /**
   * Set TTL on an existing key.
   * @param {string} key
   * @param {number} ttl - Seconds
   */
  async expire(key, ttl) {
    try { await client.expire(key, ttl); } catch {}
  },

  client
};

module.exports = cache;

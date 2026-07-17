const redis = require('redis');
require('dotenv').config();

const client = redis.createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379/0',
  socket: {
    connectTimeout: 3000,
    reconnectStrategy: (retries) => {
      if (retries > 10) {
        return new Error('Max reconnection attempts reached');
      }
      return Math.min(retries * 200, 3000);
    },
  },
});

client.on('connect', () => {
  console.log('[Redis] Connected');
});

client.on('error', (err) => {
  console.warn('[Redis] Error:', err.message);
});

client.on('reconnecting', () => {
  console.log('[Redis] Reconnecting...');
});

client.connect().catch((err) => {
  console.warn('[Redis] Initial connection failed:', err.message);
});

function getClient() { return client; }
async function set(key, value, options) { return await client.set(key, value, options); }
async function get(key) { return await client.get(key); }
async function del(key) { return await client.del(key); }
async function exists(key) { return await client.exists(key); }

module.exports = { getClient, set, get, del, exists };

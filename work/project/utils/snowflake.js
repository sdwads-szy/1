/**
 * 雪花 ID 生成器（Snowflake）
 * @description 分布式唯一 ID 生成，基于时间戳 + Worker ID + 序列号
 *              结构: [41位时间戳] [10位Worker] [12位序列号]
 * @usage const snowflake = require('../utils/snowflake');
 *        const id = snowflake.generate(); // → 字符串形式的 64 位 ID
 */

const os = require('os');

// 起始时间戳（2024-01-01T00:00:00.000Z）
const EPOCH = 1704067200000n;

// 位分配
const WORKER_ID_BITS = 10n;
const SEQUENCE_BITS = 12n;

const MAX_WORKER_ID = (1n << WORKER_ID_BITS) - 1n;   // 1023
const MAX_SEQUENCE = (1n << SEQUENCE_BITS) - 1n;     // 4095

const WORKER_ID_SHIFT = SEQUENCE_BITS;
const TIMESTAMP_SHIFT = WORKER_ID_BITS + SEQUENCE_BITS;

/**
 * 从环境变量或机器 MAC 地址派生出 Worker ID
 * @returns {bigint} 0 ~ 1023
 */
function deriveWorkerId() {
  const envId = process.env.SNOWFLAKE_WORKER_ID;
  if (envId !== undefined && envId !== '') {
    const parsed = parseInt(envId, 10);
    if (Number.isFinite(parsed) && parsed >= 0 && parsed <= Number(MAX_WORKER_ID)) {
      return BigInt(parsed);
    }
  }
  // 基于机器 hostname 哈希降级
  const hostname = os.hostname();
  let hash = 0;
  for (let i = 0; i < hostname.length; i++) {
    hash = ((hash << 5) - hash + hostname.charCodeAt(i)) | 0;
  }
  return BigInt(Math.abs(hash) % (Number(MAX_WORKER_ID) + 1));
}

class Snowflake {
  constructor() {
    this.workerId = deriveWorkerId();
    this.sequence = 0n;
    this.lastTimestamp = -1n;
  }

  /**
   * 获取当前毫秒时间戳（相对于 EPOCH）
   * @returns {bigint}
   */
  _currentTimestamp() {
    return BigInt(Date.now()) - EPOCH;
  }

  /**
   * 等待下一毫秒
   * @param {bigint} lastTimestamp
   * @returns {bigint}
   */
  _waitNextMillis(lastTimestamp) {
    let ts = this._currentTimestamp();
    while (ts <= lastTimestamp) {
      ts = this._currentTimestamp();
    }
    return ts;
  }

  /**
   * 生成唯一 ID
   * @returns {string} 雪花 ID 字符串（避免 JS Number 精度丢失）
   */
  generate() {
    let timestamp = this._currentTimestamp();

    if (timestamp < this.lastTimestamp) {
      throw new Error('SNOWFLAKE_CLOCK_BACKWARD');
    }

    if (timestamp === this.lastTimestamp) {
      this.sequence = (this.sequence + 1n) & MAX_SEQUENCE;
      if (this.sequence === 0n) {
        timestamp = this._waitNextMillis(this.lastTimestamp);
      }
    } else {
      this.sequence = 0n;
    }

    this.lastTimestamp = timestamp;

    const id = (timestamp << TIMESTAMP_SHIFT)
             | (this.workerId << WORKER_ID_SHIFT)
             | this.sequence;

    return id.toString();
  }
}

// 导出单例
module.exports = new Snowflake();

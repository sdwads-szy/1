const os = require('os');

const EPOCH = new Date('2024-01-01T00:00:00.000Z').getTime();
const WORKER_ID_BITS = 10;
const SEQUENCE_BITS = 12;
const MAX_WORKER_ID = (1 << WORKER_ID_BITS) - 1;   // 1023
const MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1;     // 4095

/**
 * 获取 Worker ID
 * 优先使用环境变量 WORKER_ID（K8s Pod IP 取模），
 * 回退到 hostname + PID 的哈希值取模
 */
function getWorkerId() {
  if (process.env.WORKER_ID !== undefined) {
    const id = parseInt(process.env.WORKER_ID, 10);
    if (!isNaN(id)) return id & MAX_WORKER_ID;
  }
  let hash = 0;
  const str = os.hostname() + String(process.pid);
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) & MAX_WORKER_ID;
}

class Snowflake {
  constructor() {
    this.workerId = getWorkerId();
    this.sequence = 0;
    this.lastTimestamp = -1;
  }

  /**
   * 生成全局唯一 ID（64-bit 雪花算法）
   * @returns {string} 数字字符串（避免 JS Number 精度丢失）
   */
  nextId() {
    let timestamp = Date.now();

    if (timestamp === this.lastTimestamp) {
      this.sequence = (this.sequence + 1) & MAX_SEQUENCE;
      if (this.sequence === 0) {
        while (timestamp <= this.lastTimestamp) {
          timestamp = Date.now();
        }
      }
    } else {
      this.sequence = 0;
    }

    this.lastTimestamp = timestamp;

    const elapsed = timestamp - EPOCH;
    const id = (BigInt(elapsed) << BigInt(WORKER_ID_BITS + SEQUENCE_BITS))
      | (BigInt(this.workerId) << BigInt(SEQUENCE_BITS))
      | BigInt(this.sequence);

    return id.toString();
  }
}

const snowflake = new Snowflake();

module.exports = snowflake;

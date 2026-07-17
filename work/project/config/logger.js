const winston = require('winston');
require('dotenv').config();

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(({ timestamp, level, message, stack, ...meta }) => {
          const metaStr = Object.keys(meta).length ? ' ' + JSON.stringify(meta) : '';
          const output = stack || message;
          return `${timestamp} [${level}]: ${output}${metaStr}`;
        })
      )
    })
  ],
  exitOnError: false,
});

function info(msg, meta) { logger.info(msg, meta); }
function error(msg, meta) { logger.error(msg, meta); }
function warn(msg, meta) { logger.warn(msg, meta); }
function debug(msg, meta) { logger.debug(msg, meta); }

module.exports = { info, error, warn, debug };

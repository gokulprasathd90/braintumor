'use strict';

const { createLogger, format, transports } = require('winston');
const path = require('path');
const fs = require('fs');
const config = require('../config');

// Ensure logs directory exists
if (!fs.existsSync(config.paths.logsDir)) {
  fs.mkdirSync(config.paths.logsDir, { recursive: true });
}

// ─── Custom format ────────────────────────────────────────────────────────────
// Produces: [2024-01-07 10:30:15] [INFO] [MODULE] message
const customFormat = format.printf(({ timestamp, level, message, module: mod, ...meta }) => {
  const moduleTag = mod ? `[${mod.toUpperCase()}]` : '[APP]';
  const metaStr = Object.keys(meta).length ? ' ' + JSON.stringify(meta) : '';
  return `[${timestamp}] [${level.toUpperCase().padEnd(5)}] ${moduleTag.padEnd(12)} ${message}${metaStr}`;
});

// ─── Console format (colourised) ─────────────────────────────────────────────
const consoleFormat = format.combine(
  format.colorize({ all: true }),
  format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  customFormat
);

// ─── File format (JSON for structured querying) ───────────────────────────────
const fileFormat = format.combine(
  format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  format.errors({ stack: true }),
  format.json()
);

// ─── Logger instance ──────────────────────────────────────────────────────────
const logger = createLogger({
  level: config.server.env === 'production' ? 'info' : 'debug',
  transports: [
    // Console — always active
    new transports.Console({
      format: consoleFormat,
    }),
    // All levels → logs/app.log
    new transports.File({
      filename: path.join(config.paths.logsDir, 'app.log'),
      format: fileFormat,
      maxsize: 5 * 1024 * 1024, // 5 MB per file
      maxFiles: 5,
      tailable: true,
    }),
    // Errors only → logs/error.log
    new transports.File({
      filename: path.join(config.paths.logsDir, 'error.log'),
      level: 'error',
      format: fileFormat,
      maxsize: 5 * 1024 * 1024,
      maxFiles: 5,
      tailable: true,
    }),
  ],
  // Do not crash on uncaught errors inside logger itself
  exitOnError: false,
});

/**
 * Returns a child logger tagged with a module name.
 * Usage: const log = require('./logger').child('FCM');
 *        log.info('Converged in 23 iterations');
 *
 * @param {string} moduleName
 * @returns winston child logger
 */
logger.child = function (moduleName) {
  return createLogger({
    level: logger.level,
    transports: logger.transports,
    defaultMeta: { module: moduleName },
    format: format.combine(
      format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
      customFormat
    ),
  });
};

module.exports = logger;

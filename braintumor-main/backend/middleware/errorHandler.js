'use strict';

const config = require('../config');
const logger = require('../utils/logger');

/**
 * Global Express error handler.
 * Must be registered LAST in server.js — after all routes.
 * Signature must have all 4 parameters for Express to recognise it.
 *
 * Response envelope (always JSON):
 * {
 *   success: false,
 *   error: {
 *     code:    <HTTP status number>,
 *     message: <human-readable string>,
 *     detail:  <stack trace — development only>
 *   }
 * }
 */
// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
  // ── Determine HTTP status code ─────────────────────────────────────────────
  let statusCode = err.statusCode || err.status || 500;

  // Multer file-size overflow
  if (err.code === 'LIMIT_FILE_SIZE')       statusCode = 413;
  // Invalid file type from upload.middleware.js
  if (err.code === 'INVALID_FILE_TYPE')     statusCode = 400;
  // SQLite unique constraint violation
  if (err.code === 'SQLITE_CONSTRAINT')     statusCode = 409;
  // SQLite generic error
  if (err.code && err.code.startsWith('SQLITE_')) statusCode = 500;

  // ── Build message ──────────────────────────────────────────────────────────
  let message = err.message || 'An unexpected error occurred.';

  // Sanitise generic 500 message in production — never leak internals
  if (statusCode === 500 && config.server.env === 'production') {
    message = 'Internal server error. Please try again later.';
  }

  // ── Log ───────────────────────────────────────────────────────────────────
  if (statusCode >= 500) {
    logger.error(`[ERROR] ${req.method} ${req.originalUrl} → ${statusCode} | ${err.message}`, {
      stack: err.stack,
    });
  } else {
    logger.warn(`[WARN]  ${req.method} ${req.originalUrl} → ${statusCode} | ${message}`);
  }

  // ── Response ──────────────────────────────────────────────────────────────
  const body = {
    success: false,
    error: {
      code:    statusCode,
      message,
    },
  };

  // Include stack trace only in development
  if (config.server.env === 'development' && err.stack) {
    body.error.detail = err.stack;
  }

  res.status(statusCode).json(body);
}

/**
 * 404 handler — catches any request that did not match a registered route.
 * Register this BEFORE errorHandler but AFTER all routes.
 */
function notFoundHandler(req, res) {
  logger.warn(`[404] ${req.method} ${req.originalUrl}`);
  res.status(404).json({
    success: false,
    error: {
      code:    404,
      message: `Route not found: ${req.method} ${req.originalUrl}`,
    },
  });
}

module.exports = { errorHandler, notFoundHandler };

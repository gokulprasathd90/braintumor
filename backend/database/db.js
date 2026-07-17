'use strict';

const { Database } = require('node-sqlite3-wasm');
const path         = require('path');
const fs           = require('fs');
const config       = require('../config');
const logger       = require('../utils/logger');

// ─── Ensure database directory exists ────────────────────────────────────────
const dbDir = path.dirname(config.database.path);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

// ─── Open connection ──────────────────────────────────────────────────────────
let _db;

try {
  _db = new Database(config.database.path);

  // WAL mode — better concurrent read performance
  _db.exec('PRAGMA journal_mode = WAL');

  // FK constraints (node-sqlite3-wasm enables FKs by default, but be explicit)
  _db.exec('PRAGMA foreign_keys = ON');

  // Increase busy timeout so concurrent writes queue instead of failing
  _db.exec('PRAGMA busy_timeout = 5000');

  logger.info(`[DB] Connected to SQLite at: ${config.database.path}`);
} catch (err) {
  logger.error(`[DB] Failed to open database: ${err.message}`);
  process.exit(1);
}

// ─── better-sqlite3 compatibility shim ───────────────────────────────────────
//
// node-sqlite3-wasm's Statement objects must be manually finalized to avoid
// memory leaks. The shim below wraps db.prepare() so that each call returns
// a thin object whose .run() / .get() / .all() methods auto-finalize the
// underlying statement — exactly matching better-sqlite3's behaviour.
//
// Additionally, db.transaction(fn) and db.pragma(str) are shimmed so that
// migrate.js and any future code can call them without modification.

const db = {
  // ── prepare(sql) → { run, get, all } ──────────────────────────────────────
  // Returns a statement-like object.  Each call to run/get/all prepares a
  // *fresh* statement, executes it, finalizes it, then returns the result.
  // This matches better-sqlite3's "prepare once, call many times" pattern at
  // the cost of re-preparing on every invocation — acceptable for this project.
  prepare(sql) {
    return {
      run(...args) {
        const stmt = _db.prepare(sql);
        try {
          // better-sqlite3 passes positional args as spread; node-sqlite3-wasm
          // expects a single value, array, or object.
          // Zero args (e.g. DDL statements) → call run() with no argument.
          if (args.length === 0) return stmt.run();
          const values = args.length === 1 ? args[0] : args;
          return stmt.run(values);
        } finally {
          stmt.finalize();
        }
      },
      get(...args) {
        const stmt = _db.prepare(sql);
        try {
          if (args.length === 0) return stmt.get();
          const values = args.length === 1 ? args[0] : args;
          return stmt.get(values);
        } finally {
          stmt.finalize();
        }
      },
      all(...args) {
        const stmt = _db.prepare(sql);
        try {
          if (args.length === 0) return stmt.all();
          const values = args.length === 1 ? args[0] : args;
          return stmt.all(values);
        } finally {
          stmt.finalize();
        }
      },
    };
  },

  // ── transaction(fn) → wrapped fn ──────────────────────────────────────────
  // Returns a function that, when called, wraps fn() in BEGIN / COMMIT and
  // rolls back automatically on error — matching better-sqlite3's behaviour.
  transaction(fn) {
    return function (...args) {
      _db.exec('BEGIN');
      try {
        const result = fn(...args);
        _db.exec('COMMIT');
        return result;
      } catch (err) {
        if (_db.inTransaction) _db.exec('ROLLBACK');
        throw err;
      }
    };
  },

  // ── pragma(str) ────────────────────────────────────────────────────────────
  // Accepts either "key = value" or "key" (read) form just like better-sqlite3.
  // For simplicity we always exec it as a PRAGMA statement and return nothing.
  pragma(str) {
    _db.exec(`PRAGMA ${str}`);
  },

  // ── close() ────────────────────────────────────────────────────────────────
  close() {
    if (_db.isOpen) {
      _db.close();
    }
  },

  // ── open (getter, mirrors better-sqlite3 db.open property) ────────────────
  get open() {
    return _db.isOpen;
  },
};

// ─── Graceful shutdown ────────────────────────────────────────────────────────
process.on('exit', () => {
  if (db.open) {
    db.close();
    logger.info('[DB] Connection closed.');
  }
});

process.on('SIGINT',  () => process.exit(0));
process.on('SIGTERM', () => process.exit(0));

module.exports = db;

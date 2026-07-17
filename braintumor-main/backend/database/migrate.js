'use strict';

const path   = require('path');
const fs     = require('fs');
const db     = require('./db');
const logger = require('../utils/logger');

/**
 * Run all schema migrations.
 * Uses CREATE TABLE IF NOT EXISTS — safe to call on every server start.
 *
 * Tables created:
 *  1. images             — raw upload metadata
 *  2. processed_images   — pipeline output paths per image
 *  3. features           — 7 GLCM features per image (Eq. 8–14)
 *  4. results            — EDN-SVM prediction + all 7 evaluation metrics
 *  5. model_metrics      — aggregate metrics from training runs
 *  6. comparison_results — per-model comparison data (Figures 9–14)
 *
 * Each table DDL lives in database/schema/*.sql.
 * This function reads and executes them in dependency order.
 */
function runMigrations() {
  logger.info('[DB] Running migrations...');

  // ── Order matters: parent tables first, FK-dependent tables second ──────────
  const schemaFiles = [
    'images.sql',           // no FK dependencies
    'processedImages.sql',  // FK → images
    'features.sql',         // FK → images
    'results.sql',          // FK → images (also creates model_metrics + comparison_results)
  ];

  const schemaDir = path.join(__dirname, 'schema');

  // Execute all DDL statements in a single transaction for atomicity
  const runAll = db.transaction(() => {
    for (const file of schemaFiles) {
      const filePath = path.join(schemaDir, file);

      if (!fs.existsSync(filePath)) {
        logger.warn(`[DB] Schema file not found, skipping: ${filePath}`);
        continue;
      }

      const sql = fs.readFileSync(filePath, 'utf-8');

      // Strip single-line SQL comments before splitting, so that files whose
      // first non-blank content is a comment block are handled correctly.
      // Then split on semicolons to handle multi-statement files (e.g. results.sql)
      const stripped = sql
        .split('\n')
        .filter(line => !line.trimStart().startsWith('--'))
        .join('\n');

      const statements = stripped
        .split(';')
        .map(s => s.trim())
        .filter(s => s.length > 0);

      for (const stmt of statements) {
        try {
          db.prepare(stmt).run();
        } catch (err) {
          // Log but do not crash — table may already exist with correct schema
          logger.warn(`[DB] Migration warning in ${file}: ${err.message}`);
        }
      }

      logger.info(`[DB] Applied schema: ${file}`);
    }
  });

  try {
    runAll();
    logger.info('[DB] All migrations completed successfully.');
  } catch (err) {
    logger.error(`[DB] Migration failed: ${err.message}`);
    throw err;
  }
}

// ─── Table existence helpers ──────────────────────────────────────────────────

/**
 * Check whether a table exists in the database.
 * @param {string} tableName
 * @returns {boolean}
 */
function tableExists(tableName) {
  const row = db
    .prepare(`SELECT name FROM sqlite_master WHERE type='table' AND name=?`)
    .get(tableName);
  return !!row;
}

/**
 * Return an array of all table names currently in the database.
 * @returns {string[]}
 */
function listTables() {
  const rows = db
    .prepare(`SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`)
    .all();
  return rows.map(r => r.name);
}

// ─── Allow standalone execution ───────────────────────────────────────────────
// node database/migrate.js
if (require.main === module) {
  runMigrations();
  logger.info(`[DB] Tables: ${listTables().join(', ')}`);
  process.exit(0);
}

module.exports = { runMigrations, tableExists, listTables };

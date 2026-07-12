'use strict';

const { createObjectCsvWriter } = require('csv-writer');
const fs   = require('fs');
const path = require('path');

// CSV column definitions — matches glcm_features.csv schema
const FEATURE_CSV_HEADERS = [
  { id: 'image_id',    title: 'image_id'    },
  { id: 'filename',    title: 'filename'    },
  { id: 'label',       title: 'label'       }, // 0 = healthy, 1 = tumor
  { id: 'entropy',     title: 'entropy'     }, // Eq. 8
  { id: 'correlation', title: 'correlation' }, // Eq. 9
  { id: 'energy',      title: 'energy'      }, // Eq. 10
  { id: 'contrast',    title: 'contrast'    }, // Eq. 11
  { id: 'mean',        title: 'mean'        }, // Eq. 12
  { id: 'std_dev',     title: 'std_dev'     }, // Eq. 13
  { id: 'variance',    title: 'variance'    }, // Eq. 14
];

/**
 * Create a csv-writer instance configured for GLCM feature output.
 * If the file already exists, new rows are appended (append: true).
 * If it does not exist, it is created with headers.
 *
 * @param {string} csvPath - absolute path to the output CSV file
 * @returns csv-writer instance
 */
function createFeatureCSVWriter(csvPath) {
  ensureCsvDir(csvPath);
  const fileExists = fs.existsSync(csvPath);
  return createObjectCsvWriter({
    path: csvPath,
    header: FEATURE_CSV_HEADERS,
    append: fileExists, // append if file exists to avoid overwriting headers
  });
}

/**
 * Write (append) an array of feature row objects to the CSV.
 *
 * Each row shape:
 *  {
 *    image_id, filename, label,
 *    entropy, correlation, energy, contrast, mean, std_dev, variance
 *  }
 *
 * @param {object} writer  - instance from createFeatureCSVWriter
 * @param {Array}  rows    - array of feature row objects
 * @returns {Promise<void>}
 */
async function writeFeatureRows(writer, rows) {
  if (!rows || rows.length === 0) return;
  await writer.writeRecords(rows);
}

/**
 * One-shot helper: create writer and immediately write all rows.
 * Useful when exporting the full training feature set at once.
 *
 * @param {string} csvPath    - absolute path to CSV
 * @param {Array}  rows       - feature row objects
 * @returns {Promise<void>}
 */
async function exportAllFeatures(csvPath, rows) {
  // For a full export, always create fresh with headers
  ensureCsvDir(csvPath);
  const writer = createObjectCsvWriter({
    path: csvPath,
    header: FEATURE_CSV_HEADERS,
    append: false,
  });
  await writer.writeRecords(rows);
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function ensureCsvDir(csvPath) {
  const dir = path.dirname(csvPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

module.exports = {
  createFeatureCSVWriter,
  writeFeatureRows,
  exportAllFeatures,
  FEATURE_CSV_HEADERS,
};

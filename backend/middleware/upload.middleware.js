'use strict';

const multer = require('multer');
const path   = require('path');
const fs     = require('fs');
const { v4: uuidv4 } = require('uuid');
const config = require('../config');
const logger = require('../utils/logger');

// ─── Ensure upload directory exists ──────────────────────────────────────────
if (!fs.existsSync(config.paths.uploadDir)) {
  fs.mkdirSync(config.paths.uploadDir, { recursive: true });
  logger.info(`[UPLOAD] Created upload directory: ${config.paths.uploadDir}`);
}

// ─── Disk storage configuration ──────────────────────────────────────────────
const storage = multer.diskStorage({
  /**
   * Save all uploads to the configured upload directory.
   */
  destination: (_req, _file, cb) => {
    cb(null, config.paths.uploadDir);
  },

  /**
   * Generate a collision-safe filename: <uuid><original-extension>
   * e.g.  3f2504e0-4f89-11d3-9a0c-0305e82c3301.jpg
   */
  filename: (_req, file, cb) => {
    const ext      = path.extname(file.originalname).toLowerCase();
    const safeName = `${uuidv4()}${ext}`;
    cb(null, safeName);
  },
});

// ─── File filter — JPEG and PNG only ─────────────────────────────────────────
function fileFilter(_req, file, cb) {
  if (config.upload.allowedMimeTypes.includes(file.mimetype)) {
    cb(null, true);
  } else {
    // Passing an Error as first arg triggers Multer's error handling path
    cb(
      Object.assign(new Error(
        `Invalid file type "${file.mimetype}". ` +
        `Only JPEG and PNG MRI images are accepted.`
      ), { code: 'INVALID_FILE_TYPE' }),
      false
    );
  }
}

// ─── Multer instance ──────────────────────────────────────────────────────────
const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: config.upload.maxFileSizeBytes, // 10 MB
    files: 1,                                  // one image per request
  },
});

// ─── Exported middleware ──────────────────────────────────────────────────────

/**
 * uploadSingle — handles a single file under the field name "image".
 * Attach to any route that expects one MRI image upload.
 *
 * On success: req.file is populated with Multer file metadata.
 * On error:   next(err) is called with a structured error object.
 */
const uploadSingle = (req, res, next) => {
  upload.single(config.upload.fieldName)(req, res, (err) => {
    if (!err) return next();

    // Multer-specific error codes
    if (err.code === 'LIMIT_FILE_SIZE') {
      return res.status(413).json({
        success: false,
        error: {
          code: 413,
          message: `File too large. Maximum allowed size is ${config.upload.maxFileSizeBytes / (1024 * 1024)} MB.`,
        },
      });
    }

    if (err.code === 'INVALID_FILE_TYPE') {
      return res.status(400).json({
        success: false,
        error: {
          code: 400,
          message: err.message,
        },
      });
    }

    if (err.code === 'LIMIT_UNEXPECTED_FILE') {
      return res.status(400).json({
        success: false,
        error: {
          code: 400,
          message: `Unexpected field. Use the field name "${config.upload.fieldName}" for the image.`,
        },
      });
    }

    // Any other Multer or filesystem error
    next(err);
  });
};

module.exports = { uploadSingle };

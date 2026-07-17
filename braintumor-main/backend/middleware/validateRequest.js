'use strict';

const db     = require('../database/db');
const logger = require('../utils/logger');
const config = require('../config');

// UUID v4 regex — used to validate every :imageId route param
const UUID_V4_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Send a structured 400 Bad Request response.
 */
function badRequest(res, message) {
  return res.status(400).json({
    success: false,
    error: { code: 400, message },
  });
}

/**
 * Send a structured 404 Not Found response.
 */
function notFound(res, message) {
  return res.status(404).json({
    success: false,
    error: { code: 404, message },
  });
}

// ─── Validators ───────────────────────────────────────────────────────────────

/**
 * validateImageId
 *
 * Middleware that:
 *  1. Checks req.params.imageId is a valid UUID v4 string.
 *  2. Verifies a record with that ID exists in the `images` table.
 *
 * Attaches the found image row to req.imageRecord for downstream use.
 */
function validateImageId(req, res, next) {
  const { imageId } = req.params;

  // 1. Format check
  if (!imageId || !UUID_V4_REGEX.test(imageId)) {
    logger.warn(`[VALIDATE] Invalid imageId format: "${imageId}"`);
    return badRequest(res, `Invalid imageId format. Expected a UUID v4, received: "${imageId}".`);
  }

  // 2. Database existence check
  const row = db
    .prepare('SELECT id, filename, raw_path, upload_time FROM images WHERE id = ?')
    .get(imageId);

  if (!row) {
    logger.warn(`[VALIDATE] imageId not found in DB: ${imageId}`);
    return notFound(res, `Image with id "${imageId}" not found. Please upload the image first.`);
  }

  // Attach record so the route handler does not need a second DB call
  req.imageRecord = row;
  next();
}

/**
 * validateSegmentParams
 *
 * Middleware that:
 *  1. Reads optional ?clusters query param (defaults to FCM config C=3).
 *  2. Validates it is an integer in the range [2, 10].
 *  3. Attaches req.clusters for the segment route.
 */
function validateSegmentParams(req, res, next) {
  const raw = req.query.clusters;

  if (raw === undefined || raw === null || raw === '') {
    // Use configured default
    req.clusters = config.fcm.clusters;
    return next();
  }

  const parsed = parseInt(raw, 10);

  if (isNaN(parsed) || parsed < 2 || parsed > 10) {
    return badRequest(
      res,
      `Invalid "clusters" parameter: "${raw}". Must be an integer between 2 and 10.`
    );
  }

  req.clusters = parsed;
  next();
}

/**
 * validateBatchUpload
 *
 * Middleware that:
 *  1. Confirms req.file was populated by Multer (file was attached).
 *  2. Checks the MIME type is in the allowed list.
 *
 * Must run AFTER uploadSingle in the route middleware chain.
 */
function validateBatchUpload(req, res, next) {
  if (!req.file) {
    return badRequest(
      res,
      `No image file received. Attach an MRI image using the field name "${config.upload.fieldName}".`
    );
  }

  if (!config.upload.allowedMimeTypes.includes(req.file.mimetype)) {
    return badRequest(
      res,
      `Invalid file type "${req.file.mimetype}". Only JPEG and PNG MRI images are accepted.`
    );
  }

  next();
}

/**
 * validateUploadFile
 *
 * Same as validateBatchUpload — checks req.file exists after Multer runs.
 * Used on POST /api/upload.
 */
function validateUploadFile(req, res, next) {
  if (!req.file) {
    return badRequest(
      res,
      `No image file received. Attach an MRI image using the field name "${config.upload.fieldName}".`
    );
  }
  next();
}

module.exports = {
  validateImageId,
  validateSegmentParams,
  validateBatchUpload,
  validateUploadFile,
};

'use strict';

const express  = require('express');
const { v4: uuidv4 } = require('uuid');
const router   = express.Router();

const db       = require('../database/db');
const { uploadSingle }      = require('../middleware/upload.middleware');
const { validateUploadFile } = require('../middleware/validateRequest');
const logger   = require('../utils/logger');

/**
 * POST /api/upload
 *
 * Accepts a single MRI image (JPEG/PNG, max 10 MB) via multipart/form-data.
 * Field name: "image"
 *
 * Pipeline:
 *  1. uploadSingle      — Multer saves file to uploads/ with UUID filename
 *  2. validateUploadFile — confirms req.file is present
 *  3. Generate record UUID
 *  4. INSERT into `images` table
 *  5. Return image_id + metadata
 *
 * Success response 201:
 *  {
 *    success:  true,
 *    data: {
 *      image_id:    "<uuid>",
 *      filename:    "original-name.jpg",
 *      raw_path:    "/uploads/<uuid>.jpg",
 *      upload_time: "2024-01-07T10:30:15.000Z",
 *      next_step:   "POST /api/preprocess/<image_id>"
 *    }
 *  }
 */
router.post('/', uploadSingle, validateUploadFile, (req, res, next) => {
  try {
    const imageId   = uuidv4();
    const now       = new Date().toISOString();
    const filename  = req.file.originalname;
    const rawPath   = req.file.path;

    // Persist to database
    db.prepare(`
      INSERT INTO images (id, filename, raw_path, upload_time)
      VALUES (?, ?, ?, ?)
    `).run(imageId, filename, rawPath, now);

    logger.info(`[UPLOAD] Saved image: ${imageId} | ${filename} | ${rawPath}`);

    return res.status(201).json({
      success: true,
      data: {
        image_id:    imageId,
        filename,
        raw_path:    rawPath,
        upload_time: now,
        next_step:   `POST /api/preprocess/${imageId}`,
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;

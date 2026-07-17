'use strict';

const express  = require('express');
const { v4: uuidv4 } = require('uuid');
const path     = require('path');
const router   = express.Router();

const db       = require('../database/db');
const { validateImageId } = require('../middleware/validateRequest');
const { startTimer }      = require('../utils/timer');
const { toStaticUrl }     = require('../utils/imageUtils');
const { resizeById }      = require('../pipeline/preprocessing/resize');
const { enhanceById }     = require('../pipeline/preprocessing/acea');
const logger   = require('../utils/logger');
const config   = require('../config');

/**
 * POST /api/preprocess/:imageId
 *
 * Preprocessing pipeline — Step 1 (resize) + Step 2 (ACEA contrast enhancement).
 * Median filter (Step 3) is wired in the next phase.
 *
 * Steps executed:
 *   1. resizeById   → dataset/processed/resized/<imageId>_resized.png
 *   2. enhanceById  → dataset/processed/enhanced/<imageId>_enhanced.png
 *
 * Both paths are persisted to processed_images table (upsert).
 * Static URLs are derived relative to the project root so the
 * frontend can load them via the /processed express.static mount.
 *
 * Success response 200:
 * {
 *   success: true,
 *   data: {
 *     image_id, resized_url, enhanced_url,
 *     acea_stats: { Pmin, Pmax, muT, muV, nV, stdT, stdV,
 *                   clippedPixels, totalPixels },
 *     computational_time_ms,
 *     next_step
 *   }
 * }
 */
router.post('/:imageId', validateImageId, async (req, res, next) => {
  const timer = startTimer();

  try {
    const { imageId }  = req.params;
    const { raw_path } = req.imageRecord;   // absolute path saved by Multer

    // ── Step 1: Resize to 256×256 ─────────────────────────────────────────
    logger.info(`[PREPROCESS] START imageId=${imageId}`);

    const resizeResult = await resizeById(imageId, raw_path);
    logger.info(`[PREPROCESS] resize done → ${path.basename(resizeResult.outputPath)}`);

    // ── Step 2: ACEA contrast enhancement ────────────────────────────────
    const aceaResult = await enhanceById(imageId, resizeResult.outputPath);
    logger.info(`[PREPROCESS] ACEA done → ${path.basename(aceaResult.outputPath)}`);

    // ── Derive static-serve URLs ──────────────────────────────────────────
    // server.js mounts:  app.use('/processed', express.static(config.paths.processedDir))
    // processedDir = <project_root>/dataset/processed
    // So an absolute path of .../dataset/processed/resized/foo.png
    // becomes the URL /processed/resized/foo.png
    const resizedUrl  = toStaticUrl(resizeResult.outputPath, config.paths.processedDir);
    const enhancedUrl = toStaticUrl(aceaResult.outputPath,  config.paths.processedDir);

    // ── Persist to processed_images table (upsert) ───────────────────────
    const now      = new Date().toISOString();
    const existing = db
      .prepare('SELECT id FROM processed_images WHERE image_id = ?')
      .get(imageId);

    if (existing) {
      db.prepare(`
        UPDATE processed_images
           SET resized_path  = ?,
               enhanced_path = ?
         WHERE image_id = ?
      `).run(resizeResult.outputPath, aceaResult.outputPath, imageId);
    } else {
      db.prepare(`
        INSERT INTO processed_images
          (id, image_id, resized_path, enhanced_path, denoised_path, segmented_path, created_at)
        VALUES (?, ?, ?, ?, NULL, NULL, ?)
      `).run(uuidv4(), imageId, resizeResult.outputPath, aceaResult.outputPath, now);
    }

    timer.stop();
    const ms = timer.elapsedMs();
    logger.info(`[PREPROCESS] DONE imageId=${imageId} | ${ms.toFixed(1)}ms`);

    return res.status(200).json({
      success: true,
      data: {
        image_id:              imageId,
        resized_url:           resizedUrl,
        enhanced_url:          enhancedUrl,
        acea_stats:            aceaResult.stats,
        computational_time_ms: parseFloat(ms.toFixed(2)),
        next_step:             `POST /api/segment/${imageId}`,
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;

'use strict';

const express = require('express');
const { v4: uuidv4 } = require('uuid');
const router  = express.Router();

const db      = require('../database/db');
const { validateImageId } = require('../middleware/validateRequest');
const { startTimer }      = require('../utils/timer');
const logger  = require('../utils/logger');

/**
 * POST /api/features/:imageId
 *
 * Extracts GLCM texture features from the FCM-segmented image.
 * All 7 features from Equations 8–14 of the paper:
 *   Entropy, Correlation, Energy, Contrast, Mean, Std Dev, Variance
 *
 * Currently returns placeholder feature values — GLCM wired in pipeline phase.
 *
 * Success response 200:
 *  {
 *    success: true,
 *    data: {
 *      image_id,
 *      features: { entropy, correlation, energy, contrast, mean, std_dev, variance },
 *      computational_time_ms,
 *      next_step
 *    }
 *  }
 */
router.post('/:imageId', validateImageId, (req, res, next) => {
  const timer = startTimer();
  try {
    const { imageId } = req.params;

    // Confirm segmentation has been done
    const processed = db
      .prepare('SELECT segmented_path FROM processed_images WHERE image_id = ?')
      .get(imageId);

    if (!processed || !processed.segmented_path) {
      return res.status(422).json({
        success: false,
        error: {
          code:    422,
          message: `Image ${imageId} has not been segmented yet. Run POST /api/segment/${imageId} first.`,
        },
      });
    }

    // ── PLACEHOLDER feature values ────────────────────────────────────────────
    // Real values computed by glcm.js + glcmFeatures.js in pipeline phase
    const features = {
      entropy:     3.4521,   // Eq. 8
      correlation: 0.7834,   // Eq. 9
      energy:      0.0612,   // Eq. 10
      contrast:    42.1870,  // Eq. 11
      mean:        128.4320, // Eq. 12
      std_dev:     38.9910,  // Eq. 13
      variance:    1520.292, // Eq. 14
    };

    const now = new Date().toISOString();

    // Upsert features record
    const existing = db
      .prepare('SELECT id FROM features WHERE image_id = ?')
      .get(imageId);

    if (existing) {
      db.prepare(`
        UPDATE features
        SET entropy=?, correlation=?, energy=?, contrast=?,
            mean=?, std_dev=?, variance=?
        WHERE image_id=?
      `).run(
        features.entropy, features.correlation, features.energy,
        features.contrast, features.mean, features.std_dev,
        features.variance, imageId
      );
    } else {
      db.prepare(`
        INSERT INTO features
          (id, image_id, entropy, correlation, energy, contrast,
           mean, std_dev, variance, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        uuidv4(), imageId,
        features.entropy, features.correlation, features.energy,
        features.contrast, features.mean, features.std_dev,
        features.variance, now
      );
    }

    timer.stop();
    logger.info(`[FEATURES] imageId=${imageId} | ${timer.elapsedMs().toFixed(1)}ms (placeholder)`);

    return res.status(200).json({
      success: true,
      data: {
        image_id:             imageId,
        features,
        computational_time_ms: timer.elapsedMs(),
        status:               'placeholder — GLCM algorithm not yet implemented',
        next_step:            `POST /api/classify/${imageId}`,
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;

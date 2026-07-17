'use strict';

const express = require('express');
const { v4: uuidv4 } = require('uuid');
const router  = express.Router();

const db      = require('../database/db');
const { validateImageId } = require('../middleware/validateRequest');
const { startTimer }      = require('../utils/timer');
const logger  = require('../utils/logger');

/**
 * POST /api/classify/:imageId
 *
 * Classifies the MRI image as "normal" or "abnormal" using the EDN-SVM model.
 * Input: GLCM feature vector stored in `features` table.
 * Output: prediction + confidence score.
 *
 * Paper target: 97.93% accuracy, 92% sensitivity, 98% specificity.
 *
 * Currently returns a placeholder prediction — EDN-SVM wired in pipeline phase.
 *
 * Success response 200:
 *  {
 *    success: true,
 *    data: {
 *      image_id, prediction, confidence,
 *      computational_time_ms, next_step
 *    }
 *  }
 */
router.post('/:imageId', validateImageId, (req, res, next) => {
  const timer = startTimer();
  try {
    const { imageId } = req.params;

    // Confirm feature extraction has been done
    const featureRow = db
      .prepare('SELECT * FROM features WHERE image_id = ?')
      .get(imageId);

    if (!featureRow) {
      return res.status(422).json({
        success: false,
        error: {
          code:    422,
          message: `Features not extracted for image ${imageId}. Run POST /api/features/${imageId} first.`,
        },
      });
    }

    // ── PLACEHOLDER prediction ────────────────────────────────────────────────
    // Real prediction from ednSvm.predict() in classifier implementation phase
    const prediction  = 'abnormal';   // "normal" | "abnormal"
    const confidence  = 0.9412;       // float [0, 1]

    timer.stop();
    const computationalTimeMs = timer.elapsedMs();
    const now = new Date().toISOString();

    // Upsert result record
    const existing = db
      .prepare('SELECT id FROM results WHERE image_id = ?')
      .get(imageId);

    if (existing) {
      db.prepare(`
        UPDATE results
        SET prediction=?, confidence=?, computational_time=?
        WHERE image_id=?
      `).run(prediction, confidence, computationalTimeMs, imageId);
    } else {
      db.prepare(`
        INSERT INTO results
          (id, image_id, prediction, confidence,
           accuracy, sensitivity, specificity,
           psnr, jaccard, ber, computational_time, created_at)
        VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?)
      `).run(uuidv4(), imageId, prediction, confidence, computationalTimeMs, now);
    }

    logger.info(`[CLASSIFY] imageId=${imageId} | prediction=${prediction} | confidence=${confidence} (placeholder)`);

    return res.status(200).json({
      success: true,
      data: {
        image_id:             imageId,
        prediction,
        confidence,
        computational_time_ms: computationalTimeMs,
        status:               'placeholder — EDN-SVM classifier not yet implemented',
        next_step:            `GET /api/results/${imageId}`,
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;

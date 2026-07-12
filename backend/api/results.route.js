'use strict';

const express = require('express');
const router  = express.Router();

const db      = require('../database/db');
const { validateImageId } = require('../middleware/validateRequest');
const logger  = require('../utils/logger');

/**
 * GET /api/results/:imageId
 *
 * Returns the complete pipeline result for a given image by joining
 * all four database tables: images, processed_images, features, results.
 *
 * Success response 200:
 *  {
 *    success: true,
 *    data: {
 *      image_id, filename, upload_time,
 *      paths:    { raw, resized, enhanced, denoised, segmented },
 *      features: { entropy, correlation, energy, contrast, mean, std_dev, variance },
 *      result:   { prediction, confidence },
 *      metrics:  { accuracy, sensitivity, specificity, psnr, jaccard, ber, computational_time }
 *    }
 *  }
 *
 * 404 is returned if imageId does not exist (caught by validateImageId middleware).
 * 202 is returned if the pipeline has not completed yet for this image.
 */
router.get('/:imageId', validateImageId, (req, res, next) => {
  try {
    const { imageId } = req.params;

    // ── Fetch processed paths ─────────────────────────────────────────────────
    const processed = db
      .prepare('SELECT * FROM processed_images WHERE image_id = ?')
      .get(imageId);

    // ── Fetch features ────────────────────────────────────────────────────────
    const featureRow = db
      .prepare('SELECT * FROM features WHERE image_id = ?')
      .get(imageId);

    // ── Fetch classification result ───────────────────────────────────────────
    const resultRow = db
      .prepare('SELECT * FROM results WHERE image_id = ?')
      .get(imageId);

    // Determine pipeline completion status
    const pipelineComplete = !!(processed && featureRow && resultRow);

    if (!pipelineComplete) {
      // Return partial data with 202 to indicate processing not complete
      return res.status(202).json({
        success: true,
        data: {
          image_id:    imageId,
          filename:    req.imageRecord.filename,
          upload_time: req.imageRecord.upload_time,
          pipeline_complete: false,
          completed_steps: {
            upload:     true,
            preprocess: !!processed,
            segment:    !!(processed && processed.segmented_path),
            features:   !!featureRow,
            classify:   !!resultRow,
          },
          paths: processed ? {
            raw:       req.imageRecord.raw_path,
            resized:   processed.resized_path   || null,
            enhanced:  processed.enhanced_path  || null,
            denoised:  processed.denoised_path  || null,
            segmented: processed.segmented_path || null,
          } : { raw: req.imageRecord.raw_path },
          features: featureRow ? {
            entropy:     featureRow.entropy,
            correlation: featureRow.correlation,
            energy:      featureRow.energy,
            contrast:    featureRow.contrast,
            mean:        featureRow.mean,
            std_dev:     featureRow.std_dev,
            variance:    featureRow.variance,
          } : null,
          result:  null,
          metrics: null,
        },
      });
    }

    logger.info(`[RESULTS] Returning full result for imageId=${imageId}`);

    // ── Full result response ──────────────────────────────────────────────────
    return res.status(200).json({
      success: true,
      data: {
        image_id:    imageId,
        filename:    req.imageRecord.filename,
        upload_time: req.imageRecord.upload_time,
        pipeline_complete: true,
        paths: {
          raw:       req.imageRecord.raw_path,
          resized:   processed.resized_path,
          enhanced:  processed.enhanced_path,
          denoised:  processed.denoised_path,
          segmented: processed.segmented_path,
        },
        features: {
          entropy:     featureRow.entropy,
          correlation: featureRow.correlation,
          energy:      featureRow.energy,
          contrast:    featureRow.contrast,
          mean:        featureRow.mean,
          std_dev:     featureRow.std_dev,
          variance:    featureRow.variance,
        },
        result: {
          prediction: resultRow.prediction,
          confidence: resultRow.confidence,
        },
        metrics: {
          accuracy:           resultRow.accuracy,
          sensitivity:        resultRow.sensitivity,
          specificity:        resultRow.specificity,
          psnr:               resultRow.psnr,
          jaccard:            resultRow.jaccard,
          ber:                resultRow.ber,
          computational_time: resultRow.computational_time,
        },
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;

'use strict';

const express = require('express');
const { v4: uuidv4 } = require('uuid');
const router  = express.Router();

const db      = require('../database/db');
const { validateImageId, validateSegmentParams } = require('../middleware/validateRequest');
const { startTimer } = require('../utils/timer');
const config  = require('../config');
const logger  = require('../utils/logger');

/**
 * POST /api/segment/:imageId
 *
 * Runs Fuzzy C-Means (FCM) segmentation on the preprocessed (denoised) image.
 * FCM divides the image into C=3 clusters: tumor, brain tissue, vessels.
 * Equations 3–7 of the paper.
 *
 * Query params:
 *  ?clusters=<int>  — override default C=3 (range 2–10, validated by middleware)
 *
 * Currently returns a placeholder response — FCM wired in pipeline phase.
 *
 * Success response 200:
 *  {
 *    success: true,
 *    data: {
 *      image_id, segmented_url, cluster_centers,
 *      num_clusters, iterations, computational_time_ms, next_step
 *    }
 *  }
 */
router.post('/:imageId', validateImageId, validateSegmentParams, (req, res, next) => {
  const timer = startTimer();
  try {
    const { imageId }  = req.params;
    const numClusters  = req.clusters; // set by validateSegmentParams

    // Fetch denoised path from processed_images
    const processed = db
      .prepare('SELECT denoised_path, segmented_path FROM processed_images WHERE image_id = ?')
      .get(imageId);

    if (!processed || !processed.denoised_path) {
      return res.status(422).json({
        success: false,
        error: {
          code:    422,
          message: `Image ${imageId} has not been preprocessed yet. Run POST /api/preprocess/${imageId} first.`,
        },
      });
    }

    // ── PLACEHOLDER: real segmented path from fcm.js in pipeline phase ───────
    const segmentedPath = processed.denoised_path
      .replace('noise_removed', 'segmented');

    // Placeholder cluster centers (will be real FCM centroid values)
    const clusterCenters = Array.from({ length: numClusters }, (_, i) =>
      parseFloat(((i + 1) * (200 / numClusters)).toFixed(2))
    );

    // Update segmented_path in DB
    db.prepare(`
      UPDATE processed_images SET segmented_path = ? WHERE image_id = ?
    `).run(segmentedPath, imageId);

    timer.stop();
    logger.info(`[SEGMENT] imageId=${imageId} | clusters=${numClusters} | ${timer.elapsedMs().toFixed(1)}ms (placeholder)`);

    return res.status(200).json({
      success: true,
      data: {
        image_id:             imageId,
        segmented_url:        segmentedPath,
        cluster_centers:      clusterCenters,
        num_clusters:         numClusters,
        iterations:           null, // populated by real FCM
        computational_time_ms: timer.elapsedMs(),
        status:               'placeholder — FCM algorithm not yet implemented',
        next_step:            `POST /api/features/${imageId}`,
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;

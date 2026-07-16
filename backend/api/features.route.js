'use strict';

/**
 * POST /api/features/:imageId
 *
 * Extracts real GLCM texture features by sending the raw MRI image to the
 * FastAPI AI service (POST /api/v1/glcm).  Returns and persists all 7 features
 * from Equations 8–14 of the paper:
 *   Entropy, Correlation, Energy, Contrast, Mean, Std Dev, Variance
 *
 * The segmentation pre-check has been removed — features are computed from
 * the raw (or preprocessed) image, not from a segmented mask.
 *
 * Success response 200:
 *  {
 *    success: true,
 *    data: {
 *      image_id,
 *      features: { entropy, correlation, energy, contrast, mean, std_dev, variance },
 *      computational_time_ms
 *    }
 *  }
 */

const express  = require('express');
const { v4: uuidv4 } = require('uuid');
const fs       = require('fs');
const path     = require('path');
const FormData = require('form-data');
const axios    = require('axios');
const router   = express.Router();

const db       = require('../database/db');
const { validateImageId } = require('../middleware/validateRequest');
const { startTimer }      = require('../utils/timer');
const logger   = require('../utils/logger');

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

router.post('/:imageId', validateImageId, async (req, res, next) => {
  const timer = startTimer();
  try {
    const { imageId } = req.params;

    // Use the preprocessed (enhanced) image when available, fall back to raw
    const processed = db
      .prepare('SELECT enhanced_path, resized_path FROM processed_images WHERE image_id = ?')
      .get(imageId);

    const imagePath = processed?.enhanced_path
      || processed?.resized_path
      || req.imageRecord.raw_path;

    if (!fs.existsSync(imagePath)) {
      return res.status(404).json({
        success: false,
        error: { code: 404, message: `Image file not found on disk: ${imagePath}` },
      });
    }

    logger.info(`[FEATURES] Extracting GLCM for imageId=${imageId} from ${path.basename(imagePath)}`);

    // ── Call FastAPI POST /api/v1/glcm ──────────────────────────────────────
    const form = new FormData();
    form.append('image', fs.createReadStream(imagePath), {
      filename:    path.basename(imagePath),
      contentType: 'image/jpeg',
    });

    let aiResponse;
    try {
      aiResponse = await axios.post(
        `${AI_SERVICE_URL}/api/v1/glcm`,
        form,
        { headers: form.getHeaders(), timeout: 30_000 }
      );
    } catch (axiosErr) {
      const detail =
        axiosErr.response?.data?.detail ||
        axiosErr.response?.data?.error?.message ||
        axiosErr.message;
      logger.error(`[FEATURES] AI service error for ${imageId}: ${detail}`);
      return res.status(502).json({
        success: false,
        error: { code: 502, message: `GLCM extraction failed: ${detail}` },
      });
    }

    const aiData = aiResponse.data?.data ?? aiResponse.data;
    const features = {
      entropy:     aiData.entropy,
      correlation: aiData.correlation,
      energy:      aiData.energy,
      contrast:    aiData.contrast,
      mean:        aiData.mean,
      std_dev:     aiData.std_dev,
      variance:    aiData.variance,
    };

    // ── Persist to features table (upsert) ──────────────────────────────────
    const now      = new Date().toISOString();
    const existing = db.prepare('SELECT id FROM features WHERE image_id = ?').get(imageId);

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
    logger.info(
      `[FEATURES] imageId=${imageId} | entropy=${features.entropy.toFixed(4)} ` +
      `energy=${features.energy.toFixed(4)} | ${timer.elapsedMs().toFixed(1)}ms`
    );

    return res.status(200).json({
      success: true,
      data: {
        image_id:             imageId,
        features,
        computational_time_ms: parseFloat(timer.elapsedMs().toFixed(2)),
        next_step:            `POST /api/classify/${imageId}`,
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;

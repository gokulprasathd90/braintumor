/**
 * test.pipeline.js — Integration Tests for Full Pipeline
 *
 * Tests the complete end-to-end pipeline on sample MRI images.
 * Uses 2 sample images: one healthy, one tumor.
 *
 * Test cases:
 *
 *  1. Full pipeline completes without errors
 *     → runFullPipeline(imageId, rawPath) resolves successfully
 *     → Returns result object with all required fields
 *
 *  2. All output image files created
 *     → resized, enhanced, denoised, segmented files exist on disk after pipeline
 *
 *  3. Feature vector has all 7 values
 *     → result.features must contain:
 *       entropy, correlation, energy, contrast, mean, stdDev, variance
 *     → None of the values should be null, undefined, or NaN
 *
 *  4. Prediction is valid
 *     → result.prediction must be "normal" or "abnormal"
 *     → result.confidence must be between 0.0 and 1.0
 *
 *  5. Database records created at each stage
 *     → images, processed_images, features, results tables all have records
 *     → All imageId foreign keys are consistent
 *
 *  6. Computational time is recorded
 *     → result.metrics.computationalTime is a positive number
 *
 * Dependencies:
 *  - backend/pipeline/pipeline.js
 *  - backend/database/db.js
 *  - Sample test images in tests/fixtures/
 */

// TODO: Implement in testing phase

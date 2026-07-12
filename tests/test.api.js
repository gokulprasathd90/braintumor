/**
 * test.api.js — API Endpoint Tests
 *
 * Tests all 9 REST API endpoints using Supertest.
 *
 * Test cases per endpoint:
 *
 *  POST /api/upload
 *   → 200 with { image_id, filename, raw_path } on valid JPG upload
 *   → 400 on missing file
 *   → 400 on wrong MIME type (e.g., PDF)
 *   → 413 on file > 10MB
 *
 *  POST /api/preprocess/:imageId
 *   → 200 with { enhanced_url, denoised_url } on valid imageId
 *   → 404 on unknown imageId
 *   → 400 on invalid UUID format
 *
 *  POST /api/segment/:imageId
 *   → 200 with { segmented_url, cluster_centers } on valid imageId
 *   → 404 if preprocessing not done yet
 *
 *  POST /api/features/:imageId
 *   → 200 with 7-element features object
 *   → 404 if segmentation not done yet
 *
 *  POST /api/classify/:imageId
 *   → 200 with { prediction, confidence }
 *   → 503 if model not trained yet
 *
 *  GET /api/results/:imageId
 *   → 200 with full result object including all paths, features, metrics
 *   → 404 on unknown imageId
 *
 *  POST /api/batch
 *   → 200 with complete result on valid JPG upload
 *   → 400 on missing file
 *
 *  GET /api/metrics
 *   → 200 with metrics object
 *   → 503 if model not trained
 *
 *  GET /api/compare
 *   → 200 with comparison object for all 5 models
 *
 * Dependencies:
 *  - supertest
 *  - backend/server.js
 */

// TODO: Implement in testing phase

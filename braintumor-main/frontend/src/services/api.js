import axios from 'axios';

// ─── Axios instance ───────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: '/api',          // proxied to http://localhost:5000 by Vite
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Response interceptor — unwrap data or throw readable error ───────────────
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const message =
      err.response?.data?.error?.message ||
      err.response?.data?.message ||
      err.message ||
      'An unexpected error occurred';
    return Promise.reject(new Error(message));
  }
);

// ─── Helper for multipart uploads ────────────────────────────────────────────
function multipart(file) {
  const fd = new FormData();
  fd.append('image', file);
  return fd;
}

// ─── API functions ────────────────────────────────────────────────────────────

/**
 * POST /api/upload
 * @param {File}     file
 * @param {function} onUploadProgress — optional Axios progress callback
 *   receives a ProgressEvent with { loaded, total }
 * @returns {{ success, data: { image_id, filename, raw_path, upload_time } }}
 */
export function uploadImage(file, onUploadProgress) {
  return api.post('/upload', multipart(file), {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...(onUploadProgress ? { onUploadProgress } : {}),
  });
}

/**
 * POST /api/preprocess/:imageId
 * @param {string} imageId
 * @returns {{ success, data: { image_id, resized_url, enhanced_url, denoised_url } }}
 */
export function preprocessImage(imageId) {
  return api.post(`/preprocess/${imageId}`);
}

/**
 * POST /api/segment/:imageId
 * @param {string} imageId
 * @param {number} clusters — default 3
 * @returns {{ success, data: { image_id, segmented_url, cluster_centers, num_clusters } }}
 */
export function segmentImage(imageId, clusters = 3) {
  return api.post(`/segment/${imageId}`, null, { params: { clusters } });
}

/**
 * POST /api/features/:imageId
 * @param {string} imageId
 * @returns {{ success, data: { image_id, features } }}
 */
export function extractFeatures(imageId) {
  return api.post(`/features/${imageId}`);
}

/**
 * POST /api/classify/:imageId
 * @param {string} imageId
 * @returns {{ success, data: { image_id, prediction, confidence } }}
 */
export function classifyImage(imageId) {
  return api.post(`/classify/${imageId}`);
}

/**
 * GET /api/results/:imageId
 * @param {string} imageId
 * @returns full result object
 */
export function getResults(imageId) {
  return api.get(`/results/${imageId}`);
}

/**
 * POST /api/batch  — full pipeline in one call
 * @param {File} file
 * @returns full pipeline result
 */
export function runBatch(file) {
  return api.post('/batch', multipart(file), {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60_000,
  });
}

/**
 * GET /api/metrics
 * @returns {{ accuracy, sensitivity, specificity, psnr, jaccard, ber, computational_time }}
 */
export function getMetrics() {
  return api.get('/metrics');
}

/**
 * GET /api/compare
 * @returns {{ models, metrics: { accuracy, sensitivity, ... } }}
 */
export function getComparison() {
  return api.get('/compare');
}

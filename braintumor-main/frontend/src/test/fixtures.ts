/**
 * src/test/fixtures.ts — Shared test data factories for all test suites.
 */

import type {
  ActiveModelInfo,
  BatchItemResult,
  BatchPredictionResult,
  CacheStats,
  DatasetInfo,
  DatasetValidationReport,
  Experiment,
  ModelInfo,
  PreprocessPreviewResult,
  PredictionMetadata,
  PredictionResult,
  QualityReport,
  TopKPrediction,
  TrainingJob,
} from '@/types';

// ── PredictionMetadata ────────────────────────────────────────────────────

export const makeMeta = (overrides: Partial<PredictionMetadata> = {}): PredictionMetadata => ({
  model_name: 'efficientnet',
  model_version: '2024-01-01T00:00:00Z',
  image_size: 224,
  class_names: ['glioma', 'meningioma', 'notumor', 'pituitary'],
  predicted_at: '2024-01-01T12:00:00Z',
  source_path: null,
  gradcam_path: null,
  ...overrides,
});

// ── TopKPrediction ────────────────────────────────────────────────────────

export const makeTopK = (): TopKPrediction[] => [
  { rank: 1, class_name: 'glioma',     class_index: 0, probability: 0.85 },
  { rank: 2, class_name: 'meningioma', class_index: 1, probability: 0.10 },
  { rank: 3, class_name: 'pituitary',  class_index: 3, probability: 0.03 },
];

// ── PredictionResult ──────────────────────────────────────────────────────

export const makePredictionResult = (
  overrides: Partial<PredictionResult> = {},
): PredictionResult => ({
  image_id: 'test-id-abc123',
  predicted_class: 'glioma',
  predicted_class_index: 0,
  confidence: 0.85,
  is_high_confidence: true,
  probabilities: {
    glioma: 0.85,
    meningioma: 0.10,
    notumor: 0.03,
    pituitary: 0.02,
  },
  top_k: makeTopK(),
  timing_ms: 42.5,
  metadata: makeMeta(),
  error: null,
  ...overrides,
});

// ── BatchPredictionResult ─────────────────────────────────────────────────

export const makeBatchItem = (
  filename: string,
  success = true,
): BatchItemResult => ({
  filename,
  success,
  result: success ? makePredictionResult({ metadata: makeMeta({ source_path: filename }) }) : null,
  error: success ? null : 'ValueError: could not decode image',
});

export const makeBatchResult = (
  overrides: Partial<BatchPredictionResult> = {},
): BatchPredictionResult => ({
  total: 3,
  succeeded: 2,
  failed: 1,
  success_rate: 0.6667,
  timing_ms: 120.5,
  model_name: 'efficientnet',
  source_type: 'list',
  class_distribution: { glioma: 2 },
  export_paths: {},
  results: [
    makeBatchItem('scan1.jpg', true),
    makeBatchItem('scan2.jpg', true),
    makeBatchItem('bad.jpg',   false),
  ],
  ...overrides,
});

// ── TrainingJob ───────────────────────────────────────────────────────────

export const makeTrainingJob = (
  overrides: Partial<TrainingJob> = {},
): TrainingJob => ({
  job_id: 'job-abc-123',
  status: 'running',
  experiment_id: 'efficientnet-20240101-120000-abcd1234',
  created_at: '2024-01-01T12:00:00Z',
  started_at: '2024-01-01T12:00:01Z',
  finished_at: null,
  result: null,
  error: null,
  ...overrides,
});

export const makeCompletedJob = (): TrainingJob =>
  makeTrainingJob({
    status: 'completed',
    finished_at: '2024-01-01T12:30:00Z',
    result: {
      final_val_accuracy: 0.973,
      training_duration_s: 1800,
      epochs_trained: 38,
    },
  });

// ── Experiment ────────────────────────────────────────────────────────────

export const makeExperiment = (
  overrides: Partial<Experiment> = {},
): Experiment => ({
  experiment_id: 'efficientnet-20240101-120000-abcd1234',
  architecture: 'efficientnet',
  status: 'completed',
  created_at: '2024-01-01T12:00:00Z',
  finished_at: '2024-01-01T12:30:00Z',
  duration_s: 1800,
  epochs_trained: 38,
  best_val_accuracy: 0.973,
  notes: '',
  ...overrides,
});

// ── ModelInfo / CacheStats ────────────────────────────────────────────────

export const makeCacheStats = (): CacheStats => ({
  capacity: 4,
  size: 1,
  cached_models: ['efficientnet'],
  total_hits: 10,
  total_misses: 2,
  hit_rate: 0.8333,
  entries: [],
});

export const makeModelInfo = (
  name: string,
  available = true,
): ModelInfo => ({
  name: name as ModelInfo['name'],
  available,
  cached: name === 'efficientnet',
  model_version: available ? '2024-01-01T00:00:00Z' : null,
  total_params: available ? 12_341_232 : null,
  model_dir: `/saved_models/${name}`,
});

export const makeModelList = (): ModelInfo[] =>
  ['cnn', 'vgg16', 'resnet50', 'efficientnet'].map((n) =>
    makeModelInfo(n, n === 'efficientnet'),
  );

export const makeActiveModel = (): ActiveModelInfo => ({
  model_name: 'efficientnet',
  available: true,
  cached: true,
  model_info: { saved_at: '2024-01-01T00:00:00Z', total_params: 12_341_232 },
  cache_stats: makeCacheStats(),
});

// ── DatasetInfo ───────────────────────────────────────────────────────────

export const makeDatasetInfo = (): DatasetInfo => ({
  classes: ['glioma', 'meningioma', 'notumor', 'pituitary'],
  class_to_index: { glioma: 0, meningioma: 1, notumor: 2, pituitary: 3 },
  total_per_split: { train: 2184, val: 467, test: 467 },
  total_images: 3118,
  imbalance_ratio: 1.02,
  is_balanced: true,
  per_class_counts: {
    glioma:     { train: 546, val: 117, test: 117 },
    meningioma: { train: 546, val: 117, test: 117 },
    notumor:    { train: 546, val: 117, test: 117 },
    pituitary:  { train: 546, val: 116, test: 116 },
  },
});

export const makeValidationReport = (
  isValid = true,
): DatasetValidationReport => ({
  is_valid: isValid,
  classes_found: ['glioma', 'meningioma', 'notumor', 'pituitary'],
  class_counts: { glioma: 1321, meningioma: 1339, notumor: 500, pituitary: 1457 },
  total_images: 4617,
  errors: isValid ? [] : ['Class "notumor" has fewer than 10 images'],
  warnings: [],
});

// ── QualityReport / PreprocessPreviewResult ───────────────────────────────

export const makeQualityReport = (isValid = true): QualityReport => ({
  is_valid: isValid,
  image_width: 224,
  image_height: 224,
  file_size_bytes: 34_000,
  checks: [
    { name: 'file_size',      passed: true, value: 34000, threshold: 10485760, message: 'OK' },
    { name: 'dimensions',     passed: true, value: 224,   threshold: 32,        message: 'OK' },
    { name: 'channels',       passed: true, value: 3,     threshold: 1,         message: 'OK' },
    { name: 'mean_intensity', passed: isValid, value: 128, threshold: 10,       message: isValid ? 'OK' : 'Image too dark' },
    { name: 'sharpness',      passed: true, value: 312.1, threshold: 50,        message: 'OK' },
    { name: 'pixel_variance', passed: true, value: 64.3,  threshold: 10,        message: 'OK' },
  ],
  warnings: [],
  errors: isValid ? [] : ['mean_intensity: image may be too dark or blank'],
});

export const makePreviewResult = (): PreprocessPreviewResult => ({
  quality: makeQualityReport(true),
  config: { image_size: 224, apply_denoise: true, apply_clahe: true },
  preprocessed_b64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  augmented_b64: [
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  ],
});

// ── Helpers ───────────────────────────────────────────────────────────────

export const makeFile = (name = 'scan.jpg', type = 'image/jpeg', size = 10_240): File => {
  const buf = new Uint8Array(size).fill(0);
  return new File([buf], name, { type });
};

export const makeZipFile = (name = 'images.zip'): File => {
  const buf = new Uint8Array(100).fill(0);
  return new File([buf], name, { type: 'application/zip' });
};

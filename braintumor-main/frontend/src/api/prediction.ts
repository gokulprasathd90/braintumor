/**
 * src/api/prediction.ts — Prediction API endpoints.
 *
 * Maps to:
 *   POST /api/v1/predict/image
 *   POST /api/v1/predict/batch
 *   POST /api/v1/predict/zip
 */

import { apiClient } from './client';
import type {
  ApiResponse,
  BatchPredictionResult,
  PredictionResult,
} from '@/types';

// ── Single-image inference ─────────────────────────────────────────────────

export interface PredictImageOptions {
  modelName?: string;
  topK?: number;
  generateGradcam?: boolean;
  confidenceThreshold?: number;
  onUploadProgress?: (percent: number) => void;
}

export async function predictImage(
  file: File,
  options: PredictImageOptions = {},
): Promise<PredictionResult> {
  const {
    modelName,
    topK = 1,
    generateGradcam = false,
    confidenceThreshold = 0.5,
    onUploadProgress,
  } = options;

  const fd = new FormData();
  fd.append('image', file);
  if (modelName) fd.append('model_name', modelName);
  fd.append('top_k', String(topK));
  fd.append('generate_gradcam', String(generateGradcam));
  fd.append('confidence_threshold', String(confidenceThreshold));

  const res = await apiClient.post<ApiResponse<PredictionResult>>(
    '/predict/image',
    fd,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onUploadProgress
        ? (evt) => {
            if (evt.total) {
              onUploadProgress(Math.round((evt.loaded / evt.total) * 100));
            }
          }
        : undefined,
    },
  );
  return res.data.data;
}

// ── Batch inference ────────────────────────────────────────────────────────

export interface PredictBatchOptions {
  modelName?: string;
  topK?: number;
  generateGradcam?: boolean;
}

export async function predictBatch(
  files: File[],
  options: PredictBatchOptions = {},
): Promise<BatchPredictionResult> {
  const { modelName, topK = 1, generateGradcam = false } = options;

  const fd = new FormData();
  files.forEach((f) => fd.append('images', f));
  if (modelName) fd.append('model_name', modelName);
  fd.append('top_k', String(topK));
  fd.append('generate_gradcam', String(generateGradcam));

  const res = await apiClient.post<ApiResponse<BatchPredictionResult>>(
    '/predict/batch',
    fd,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return res.data.data;
}

// ── ZIP inference ──────────────────────────────────────────────────────────

export async function predictZip(
  archive: File,
  options: PredictBatchOptions = {},
): Promise<BatchPredictionResult> {
  const { modelName, topK = 1, generateGradcam = false } = options;

  const fd = new FormData();
  fd.append('archive', archive);
  if (modelName) fd.append('model_name', modelName);
  fd.append('top_k', String(topK));
  fd.append('generate_gradcam', String(generateGradcam));

  const res = await apiClient.post<ApiResponse<BatchPredictionResult>>(
    '/predict/zip',
    fd,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return res.data.data;
}

/**
 * src/api/dataset.ts — Dataset management API endpoints.
 *
 * Maps to:
 *   GET  /api/v1/dataset/info
 *   POST /api/v1/dataset/validate
 *   POST /api/v1/dataset/prepare
 */

import { get, post } from './client';
import type {
  ApiResponse,
  DatasetInfo,
  DatasetPrepareRequest,
  DatasetValidationReport,
} from '@/types';

// ── Dataset info ───────────────────────────────────────────────────────────

interface DatasetInfoResponse {
  success: boolean;
  data: DatasetInfo;
  message: string;
}

export async function getDatasetInfo(
  processedDir?: string,
): Promise<DatasetInfo> {
  const query = processedDir
    ? `?processed_dir=${encodeURIComponent(processedDir)}`
    : '';
  const res = await get<DatasetInfoResponse>(`/dataset/info${query}`);
  return res.data;
}

// ── Validate dataset ───────────────────────────────────────────────────────

interface DatasetValidateResponse {
  success: boolean;
  data: DatasetValidationReport;
  message: string;
}

export async function validateDataset(
  rawDir?: string,
  minImagesPerClass = 10,
): Promise<DatasetValidationReport> {
  const res = await post<DatasetValidateResponse>('/dataset/validate', {
    raw_dir: rawDir ?? null,
    min_images_per_class: minImagesPerClass,
  });
  return res.data;
}

// ── Prepare dataset ────────────────────────────────────────────────────────

export async function prepareDataset(
  req: Partial<DatasetPrepareRequest> = {},
): Promise<{ data: DatasetInfo; message: string }> {
  const body: DatasetPrepareRequest = {
    train_ratio: 0.7,
    val_ratio: 0.15,
    test_ratio: 0.15,
    seed: 42,
    overwrite: false,
    full_stats: false,
    ...req,
  };

  const res = await post<DatasetInfoResponse>('/dataset/prepare', body);
  return { data: res.data, message: res.message };
}

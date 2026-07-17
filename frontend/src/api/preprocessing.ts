/**
 * src/api/preprocessing.ts — Preprocessing API endpoints.
 *
 * Maps to:
 *   POST /api/v1/preprocess/quality-check
 *   POST /api/v1/preprocess/preview
 */

import { apiClient } from './client';
import type {
  ApiResponse,
  PreprocessPreviewResult,
  QualityReport,
} from '@/types';

// ── Quality check ──────────────────────────────────────────────────────────

export interface QualityCheckOptions {
  imageSize?: number;
  applyDenoise?: boolean;
  applyClahe?: boolean;
  claheClipLimit?: number;
  denoiseKernelSize?: number;
}

export async function qualityCheck(
  file: File,
  opts: QualityCheckOptions = {},
): Promise<{ success: boolean; data: QualityReport; message: string }> {
  const fd = new FormData();
  fd.append('image', file);
  if (opts.imageSize !== undefined) fd.append('image_size', String(opts.imageSize));
  if (opts.applyDenoise !== undefined) fd.append('apply_denoise', String(opts.applyDenoise));
  if (opts.applyClahe !== undefined) fd.append('apply_clahe', String(opts.applyClahe));
  if (opts.claheClipLimit !== undefined) fd.append('clahe_clip_limit', String(opts.claheClipLimit));
  if (opts.denoiseKernelSize !== undefined)
    fd.append('denoise_kernel_size', String(opts.denoiseKernelSize));

  const res = await apiClient.post<{
    success: boolean;
    data: QualityReport;
    message: string;
  }>('/preprocess/quality-check', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

// ── Preprocessing preview ──────────────────────────────────────────────────

export interface PreviewOptions extends QualityCheckOptions {
  includeAugmented?: boolean;
  nAugmented?: number;
}

export async function preprocessPreview(
  file: File,
  opts: PreviewOptions = {},
): Promise<{ success: boolean; data: PreprocessPreviewResult; message: string }> {
  const fd = new FormData();
  fd.append('image', file);
  if (opts.imageSize !== undefined) fd.append('image_size', String(opts.imageSize));
  if (opts.applyDenoise !== undefined) fd.append('apply_denoise', String(opts.applyDenoise));
  if (opts.applyClahe !== undefined) fd.append('apply_clahe', String(opts.applyClahe));
  if (opts.claheClipLimit !== undefined) fd.append('clahe_clip_limit', String(opts.claheClipLimit));
  if (opts.denoiseKernelSize !== undefined)
    fd.append('denoise_kernel_size', String(opts.denoiseKernelSize));
  fd.append('include_augmented', String(opts.includeAugmented ?? true));
  fd.append('n_augmented', String(opts.nAugmented ?? 4));

  const res = await apiClient.post<{
    success: boolean;
    data: PreprocessPreviewResult;
    message: string;
  }>('/preprocess/preview', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

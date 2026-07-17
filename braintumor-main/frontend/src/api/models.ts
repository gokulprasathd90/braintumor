/**
 * src/api/models.ts — Model management API endpoints.
 *
 * Maps to:
 *   GET  /api/v1/models
 *   GET  /api/v1/models/active
 *   POST /api/v1/models/reload
 */

import { get, post } from './client';
import type { ActiveModelInfo, CacheStats, ModelInfo } from '@/types';

// ── List all models ────────────────────────────────────────────────────────

interface ModelListResponse {
  success: boolean;
  data: ModelInfo[];
  cache_stats: CacheStats;
}

export interface ModelListResult {
  models: ModelInfo[];
  cache_stats: CacheStats;
}

export async function listModels(): Promise<ModelListResult> {
  const res = await get<ModelListResponse>('/models');
  return { models: res.data, cache_stats: res.cache_stats };
}

// ── Active model ───────────────────────────────────────────────────────────

interface ActiveModelResponse {
  success: boolean;
  data: ActiveModelInfo;
}

export async function getActiveModel(): Promise<ActiveModelInfo> {
  const res = await get<ActiveModelResponse>('/models/active');
  return res.data;
}

// ── Reload model ───────────────────────────────────────────────────────────

interface ReloadModelResponse {
  success: boolean;
  message: string;
  model_name: string;
}

export async function reloadModel(
  modelName: string,
): Promise<ReloadModelResponse> {
  return post<ReloadModelResponse>('/models/reload', {
    model_name: modelName,
  });
}

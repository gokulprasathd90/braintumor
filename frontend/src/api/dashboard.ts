/**
 * src/api/dashboard.ts — Dashboard / Metrics API endpoints.
 *
 * Maps to:
 *   GET /api/v1/dashboard/overview
 *   GET /api/v1/dashboard/system
 *   GET /api/v1/dashboard/inference
 *   GET /api/v1/dashboard/training
 *   GET /api/v1/dashboard/history
 */

import { get } from './client';
import type {
  DashboardOverview,
  SystemMetrics,
  InferenceMetrics,
  TrainingMetrics,
  DashboardHistory,
} from '@/types';

// ── Response envelopes ─────────────────────────────────────────────────────

interface DashboardResponse<T> {
  success: boolean;
  data: T;
}

interface DashboardHistoryResponse {
  success: boolean;
  data: DashboardHistory;
}

// ── Overview ───────────────────────────────────────────────────────────────

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const res = await get<DashboardResponse<DashboardOverview>>('/dashboard/overview');
  return res.data;
}

// ── System metrics ─────────────────────────────────────────────────────────

export async function getSystemMetrics(): Promise<SystemMetrics> {
  const res = await get<DashboardResponse<SystemMetrics>>('/dashboard/system');
  return res.data;
}

// ── Inference metrics ──────────────────────────────────────────────────────

export async function getInferenceMetrics(): Promise<InferenceMetrics> {
  const res = await get<DashboardResponse<InferenceMetrics>>('/dashboard/inference');
  return res.data;
}

// ── Training metrics ───────────────────────────────────────────────────────

export async function getTrainingMetrics(): Promise<TrainingMetrics> {
  const res = await get<DashboardResponse<TrainingMetrics>>('/dashboard/training');
  return res.data;
}

// ── Rolling history ────────────────────────────────────────────────────────

export type HistoryMetricType = 'system' | 'inference' | 'training' | 'overview';

export interface GetHistoryOptions {
  metric_type?: HistoryMetricType;
  hours?: number;
}

export async function getDashboardHistory(
  opts: GetHistoryOptions = {},
): Promise<DashboardHistory> {
  const params = new URLSearchParams();
  if (opts.metric_type) params.set('metric_type', opts.metric_type);
  if (opts.hours !== undefined) params.set('hours', String(opts.hours));
  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await get<DashboardHistoryResponse>(`/dashboard/history${query}`);
  return res.data;
}

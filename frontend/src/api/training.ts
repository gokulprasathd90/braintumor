/**
 * src/api/training.ts — Training API endpoints.
 *
 * Maps to:
 *   POST /api/v1/train/start
 *   GET  /api/v1/train/status/{job_id}
 *   GET  /api/v1/train/experiments
 *   GET  /api/v1/train/experiments/{experiment_id}
 */

import { get, post } from './client';
import type {
  Experiment,
  TrainingJob,
  TrainingStartRequest,
} from '@/types';

// ── Start a training job ───────────────────────────────────────────────────

export interface TrainStartResponse {
  success: boolean;
  message: string;
  job_id: string;
  experiment_id: string;
}

export async function startTraining(
  req: TrainingStartRequest,
): Promise<TrainStartResponse> {
  return post<TrainStartResponse>('/train/start', req);
}

// ── Poll job status ────────────────────────────────────────────────────────

interface TrainStatusResponse {
  success: boolean;
  data: TrainingJob;
}

export async function getTrainingStatus(jobId: string): Promise<TrainingJob> {
  const res = await get<TrainStatusResponse>(`/train/status/${jobId}`);
  return res.data;
}

// ── List experiments ───────────────────────────────────────────────────────

interface ExperimentListResponse {
  success: boolean;
  data: Experiment[];
  total: number;
}

export interface ListExperimentsOptions {
  architecture?: string;
  status?: string;
  limit?: number;
}

export async function listExperiments(
  opts: ListExperimentsOptions = {},
): Promise<Experiment[]> {
  const params = new URLSearchParams();
  if (opts.architecture) params.set('architecture', opts.architecture);
  if (opts.status) params.set('exp_status', opts.status);
  if (opts.limit !== undefined) params.set('limit', String(opts.limit));

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await get<ExperimentListResponse>(`/train/experiments${query}`);
  return res.data;
}

// ── Get single experiment ──────────────────────────────────────────────────

interface ExperimentDetailResponse {
  success: boolean;
  data: Experiment;
}

export async function getExperiment(
  experimentId: string,
): Promise<Experiment> {
  const res = await get<ExperimentDetailResponse>(
    `/train/experiments/${experimentId}`,
  );
  return res.data;
}

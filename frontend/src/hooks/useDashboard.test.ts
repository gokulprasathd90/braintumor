/**
 * src/hooks/useDashboard.test.ts
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import {
  useDashboard,
  useSystemMetrics,
  useInferenceMetrics,
  useTrainingMetrics,
} from './useDashboard';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

// ── Fixtures ───────────────────────────────────────────────────────────────

const OVERVIEW = {
  timestamp: '2024-07-14T12:00:00Z',
  service_version: '1.0.0',
  system: { cpu_percent: 34.1, ram_percent: 60.0, disk_percent: 42.0, gpu_available: false, uptime_seconds: 3600, platform: 'Linux', ram_used_mb: 4096 },
  inference: { total_predictions: 100, succeeded: 98, failed: 2, success_rate: 0.98, avg_latency_ms: 38.4, p95_latency_ms: null, top_classes: [], batch_runs: 3 },
  training: { total_jobs: 5, running_jobs: 0, completed_jobs: 4, failed_jobs: 1, best_val_accuracy: 0.97, total_experiments: 4 },
  models: {},
  alerts: [],
};

const SYSTEM = {
  timestamp: '2024-07-14T12:00:00Z', uptime_seconds: 3612, platform: 'Linux',
  python_version: '3.11.0', cpu_percent: 34.1, cpu_per_core: [], cpu_count_logical: 4,
  cpu_count_physical: 2, cpu_freq_mhz: null, ram_total_mb: 8192, ram_used_mb: 4201,
  ram_available_mb: 3991, ram_percent: 51.3, disk_total_gb: 256, disk_used_gb: 109,
  disk_free_gb: 147, disk_percent: 42.7, gpu_available: false, gpu_count: 0, gpus: [],
  process_pid: 1234, process_cpu_percent: 2.1, process_ram_mb: 412.8, process_threads: 8,
};

const INFERENCE = {
  timestamp: '2024-07-14T12:00:00Z', started_at: '2024-07-14T10:00:00Z',
  total_predictions: 142, succeeded: 138, failed: 4, success_rate: 0.97,
  per_model_counts: {}, avg_latency_ms: 38.4, min_latency_ms: null, max_latency_ms: null,
  p95_latency_ms: null, confidence_distribution: { buckets: [], counts: [] },
  class_distribution: {}, top_classes: [], batch_runs: 3,
  batch_images_processed: 45, batch_succeeded: 43, batch_failed: 2, recent_predictions: [],
};

const TRAINING = {
  timestamp: '2024-07-14T12:00:00Z', total_jobs: 7, queued_jobs: 0, running_jobs: 0,
  completed_jobs: 6, failed_jobs: 1, avg_job_duration_s: 1800, architecture_counts: {},
  recent_jobs: [], total_experiments: 6, best_val_accuracy: 0.97, recent_experiments: [],
};

// ── useDashboard ───────────────────────────────────────────────────────────

describe('useDashboard', () => {
  it('starts with loading=true', () => {
    mock.onGet('/dashboard/overview').reply(200, { success: true, data: OVERVIEW });
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    mock.onGet('/dashboard/inference').reply(200, { success: true, data: INFERENCE });
    mock.onGet('/dashboard/training').reply(200, { success: true, data: TRAINING });
    const { result } = renderHook(() => useDashboard({ pollInterval: 0 }));
    expect(result.current.loading).toBe(true);
  });

  it('sets loading=false after fetch', async () => {
    mock.onGet('/dashboard/overview').reply(200, { success: true, data: OVERVIEW });
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    mock.onGet('/dashboard/inference').reply(200, { success: true, data: INFERENCE });
    mock.onGet('/dashboard/training').reply(200, { success: true, data: TRAINING });
    const { result } = renderHook(() => useDashboard({ pollInterval: 0 }));
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it('populates overview after fetch', async () => {
    mock.onGet('/dashboard/overview').reply(200, { success: true, data: OVERVIEW });
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    mock.onGet('/dashboard/inference').reply(200, { success: true, data: INFERENCE });
    mock.onGet('/dashboard/training').reply(200, { success: true, data: TRAINING });
    const { result } = renderHook(() => useDashboard({ pollInterval: 0 }));
    await waitFor(() => expect(result.current.overview).not.toBeNull());
    expect(result.current.overview?.training.total_jobs).toBe(5);
  });

  it('only fetches requested domains', async () => {
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    const { result } = renderHook(() =>
      useDashboard({ pollInterval: 0, domains: ['system'] }),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.system).not.toBeNull();
    expect(result.current.overview).toBeNull();
    expect(result.current.inference).toBeNull();
  });

  it('sets lastUpdated after fetch', async () => {
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    const { result } = renderHook(() =>
      useDashboard({ pollInterval: 0, domains: ['system'] }),
    );
    await waitFor(() => expect(result.current.lastUpdated).not.toBeNull());
    expect(result.current.lastUpdated).toBeInstanceOf(Date);
  });

  it('refresh() triggers a new fetch', async () => {
    let callCount = 0;
    mock.onGet('/dashboard/system').reply(() => {
      callCount++;
      return [200, { success: true, data: SYSTEM }];
    });
    const { result } = renderHook(() =>
      useDashboard({ pollInterval: 0, domains: ['system'] }),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    const before = callCount;
    result.current.refresh();
    await waitFor(() => expect(callCount).toBeGreaterThan(before));
  });

  it('handles network error gracefully', async () => {
    mock.onGet('/dashboard/system').networkError();
    const { result } = renderHook(() =>
      useDashboard({ pollInterval: 0, domains: ['system'] }),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    // Should not crash — data stays null
    expect(result.current.system).toBeNull();
  });
});

// ── Focused hooks ──────────────────────────────────────────────────────────

describe('useSystemMetrics', () => {
  it('returns system data', async () => {
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    const { result } = renderHook(() => useSystemMetrics(0));
    await waitFor(() => expect(result.current.data).not.toBeNull());
    expect(result.current.data?.cpu_percent).toBe(34.1);
  });
});

describe('useInferenceMetrics', () => {
  it('returns inference data', async () => {
    mock.onGet('/dashboard/inference').reply(200, { success: true, data: INFERENCE });
    const { result } = renderHook(() => useInferenceMetrics(0));
    await waitFor(() => expect(result.current.data).not.toBeNull());
    expect(result.current.data?.total_predictions).toBe(142);
  });
});

describe('useTrainingMetrics', () => {
  it('returns training data', async () => {
    mock.onGet('/dashboard/training').reply(200, { success: true, data: TRAINING });
    const { result } = renderHook(() => useTrainingMetrics(0));
    await waitFor(() => expect(result.current.data).not.toBeNull());
    expect(result.current.data?.total_jobs).toBe(7);
  });
});

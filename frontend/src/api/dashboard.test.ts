/**
 * src/api/dashboard.test.ts — Unit tests for the dashboard API module.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import {
  getDashboardOverview,
  getSystemMetrics,
  getInferenceMetrics,
  getTrainingMetrics,
  getDashboardHistory,
} from '@/api/dashboard';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

// ── Fixtures ───────────────────────────────────────────────────────────────

const OVERVIEW = {
  timestamp: '2024-07-14T12:00:00Z',
  service_version: '1.0.0',
  system: { cpu_percent: 34.1, ram_percent: 60.0, disk_percent: 42.0, gpu_available: false, uptime_seconds: 3600, platform: 'Linux', ram_used_mb: 4096 },
  inference: { total_predictions: 100, succeeded: 98, failed: 2, success_rate: 0.98, avg_latency_ms: 38.4, p95_latency_ms: 74.1, top_classes: [], batch_runs: 3 },
  training: { total_jobs: 5, running_jobs: 0, completed_jobs: 4, failed_jobs: 1, best_val_accuracy: 0.973, total_experiments: 4 },
  models: {},
  alerts: [],
};

const SYSTEM = {
  timestamp: '2024-07-14T12:00:00Z',
  uptime_seconds: 3612.4,
  platform: 'Linux',
  python_version: '3.11.0',
  cpu_percent: 34.1, cpu_per_core: [28.0, 40.2], cpu_count_logical: 4, cpu_count_physical: 2, cpu_freq_mhz: 2400,
  ram_total_mb: 8192, ram_used_mb: 4201, ram_available_mb: 3991, ram_percent: 51.3,
  disk_total_gb: 256, disk_used_gb: 109.3, disk_free_gb: 146.7, disk_percent: 42.7,
  gpu_available: false, gpu_count: 0, gpus: [],
  process_pid: 1234, process_cpu_percent: 2.1, process_ram_mb: 412.8, process_threads: 8,
};

const INFERENCE = {
  timestamp: '2024-07-14T12:00:00Z',
  started_at: '2024-07-14T10:00:00Z',
  total_predictions: 142, succeeded: 138, failed: 4, success_rate: 0.9718,
  per_model_counts: { efficientnet: 138 },
  avg_latency_ms: 38.4, min_latency_ms: 12.1, max_latency_ms: 240.0, p95_latency_ms: 74.1,
  confidence_distribution: { buckets: ['<50%', '50–70%', '70–80%', '80–90%', '90–95%', '95–100%'], counts: [1, 2, 3, 10, 20, 102] },
  class_distribution: { glioma: 67, notumor: 44, meningioma: 21, pituitary: 10 },
  top_classes: [{ class_name: 'glioma', count: 67 }],
  batch_runs: 3, batch_images_processed: 45, batch_succeeded: 43, batch_failed: 2,
  recent_predictions: [],
};

const TRAINING = {
  timestamp: '2024-07-14T12:00:00Z',
  total_jobs: 7, queued_jobs: 0, running_jobs: 0, completed_jobs: 6, failed_jobs: 1,
  avg_job_duration_s: 1800.0,
  architecture_counts: { efficientnet: 4, resnet50: 2, cnn: 1 },
  recent_jobs: [],
  total_experiments: 6, best_val_accuracy: 0.9732, recent_experiments: [],
};

const HISTORY = {
  metric_type: 'system', hours: 24, count: 2,
  data: [
    { timestamp: '2024-07-14T10:00:00Z', type: 'system', cpu_percent: 30.0 },
    { timestamp: '2024-07-14T11:00:00Z', type: 'system', cpu_percent: 35.0 },
  ],
};

// ── getDashboardOverview ───────────────────────────────────────────────────

describe('getDashboardOverview', () => {
  it('returns overview data on success', async () => {
    mock.onGet('/dashboard/overview').reply(200, { success: true, data: OVERVIEW });
    const result = await getDashboardOverview();
    expect(result.timestamp).toBe('2024-07-14T12:00:00Z');
    expect(result.alerts).toEqual([]);
  });

  it('returns system sub-object', async () => {
    mock.onGet('/dashboard/overview').reply(200, { success: true, data: OVERVIEW });
    const result = await getDashboardOverview();
    expect(result.system.cpu_percent).toBe(34.1);
    expect(result.system.gpu_available).toBe(false);
  });

  it('returns inference sub-object', async () => {
    mock.onGet('/dashboard/overview').reply(200, { success: true, data: OVERVIEW });
    const result = await getDashboardOverview();
    expect(result.inference.total_predictions).toBe(100);
    expect(result.inference.success_rate).toBe(0.98);
  });

  it('returns training sub-object', async () => {
    mock.onGet('/dashboard/overview').reply(200, { success: true, data: OVERVIEW });
    const result = await getDashboardOverview();
    expect(result.training.total_jobs).toBe(5);
    expect(result.training.best_val_accuracy).toBe(0.973);
  });

  it('throws on 500 error', async () => {
    mock.onGet('/dashboard/overview').reply(500);
    await expect(getDashboardOverview()).rejects.toBeTruthy();
  });

  it('includes alerts when present', async () => {
    const withAlert = {
      ...OVERVIEW,
      alerts: [{ level: 'warning', domain: 'system', message: 'CPU high' }],
    };
    mock.onGet('/dashboard/overview').reply(200, { success: true, data: withAlert });
    const result = await getDashboardOverview();
    expect(result.alerts).toHaveLength(1);
    expect(result.alerts[0].level).toBe('warning');
  });
});

// ── getSystemMetrics ───────────────────────────────────────────────────────

describe('getSystemMetrics', () => {
  it('returns system metrics data', async () => {
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    const result = await getSystemMetrics();
    expect(result.cpu_percent).toBe(34.1);
    expect(result.platform).toBe('Linux');
  });

  it('includes gpu info', async () => {
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    const result = await getSystemMetrics();
    expect(result.gpu_available).toBe(false);
    expect(Array.isArray(result.gpus)).toBe(true);
  });

  it('includes process metrics', async () => {
    mock.onGet('/dashboard/system').reply(200, { success: true, data: SYSTEM });
    const result = await getSystemMetrics();
    expect(result.process_pid).toBe(1234);
    expect(result.process_ram_mb).toBe(412.8);
  });
});

// ── getInferenceMetrics ────────────────────────────────────────────────────

describe('getInferenceMetrics', () => {
  it('returns inference metrics data', async () => {
    mock.onGet('/dashboard/inference').reply(200, { success: true, data: INFERENCE });
    const result = await getInferenceMetrics();
    expect(result.total_predictions).toBe(142);
    expect(result.success_rate).toBe(0.9718);
  });

  it('includes confidence distribution', async () => {
    mock.onGet('/dashboard/inference').reply(200, { success: true, data: INFERENCE });
    const result = await getInferenceMetrics();
    expect(result.confidence_distribution.buckets).toHaveLength(6);
    expect(result.confidence_distribution.counts).toHaveLength(6);
  });

  it('includes class distribution', async () => {
    mock.onGet('/dashboard/inference').reply(200, { success: true, data: INFERENCE });
    const result = await getInferenceMetrics();
    expect(result.class_distribution.glioma).toBe(67);
  });
});

// ── getTrainingMetrics ─────────────────────────────────────────────────────

describe('getTrainingMetrics', () => {
  it('returns training metrics data', async () => {
    mock.onGet('/dashboard/training').reply(200, { success: true, data: TRAINING });
    const result = await getTrainingMetrics();
    expect(result.total_jobs).toBe(7);
    expect(result.completed_jobs).toBe(6);
  });

  it('includes architecture counts', async () => {
    mock.onGet('/dashboard/training').reply(200, { success: true, data: TRAINING });
    const result = await getTrainingMetrics();
    expect(result.architecture_counts.efficientnet).toBe(4);
  });
});

// ── getDashboardHistory ────────────────────────────────────────────────────

describe('getDashboardHistory', () => {
  it('returns history data with defaults', async () => {
    mock.onGet('/dashboard/history').reply(200, { success: true, data: HISTORY });
    const result = await getDashboardHistory();
    expect(result.metric_type).toBe('system');
    expect(result.count).toBe(2);
  });

  it('passes metric_type query param', async () => {
    mock.onGet('/dashboard/history?metric_type=inference&hours=6').reply(200, {
      success: true,
      data: { ...HISTORY, metric_type: 'inference', hours: 6, count: 0, data: [] },
    });
    const result = await getDashboardHistory({ metric_type: 'inference', hours: 6 });
    expect(result.metric_type).toBe('inference');
  });

  it('data array is returned', async () => {
    mock.onGet('/dashboard/history').reply(200, { success: true, data: HISTORY });
    const result = await getDashboardHistory();
    expect(Array.isArray(result.data)).toBe(true);
    expect(result.data).toHaveLength(2);
  });
});

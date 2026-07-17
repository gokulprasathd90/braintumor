/**
 * src/api/performance.test.ts — Unit tests for the performance API module.
 *
 * Covers all functions exported from src/api/performance.ts:
 *   getPerformanceSummary, getProfilerSummary, getMemoryReport,
 *   getCacheReport, getApiStats, getConcurrencyReport,
 *   runBenchmark, getBenchmarkResult, runSingleBenchmark, resetProfiler
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import {
  getPerformanceSummary,
  getProfilerSummary,
  getMemoryReport,
  getCacheReport,
  getApiStats,
  getConcurrencyReport,
  runBenchmark,
  getBenchmarkResult,
  runSingleBenchmark,
  resetProfiler,
} from '@/api/performance';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => mock.reset());

// ── Fixtures ───────────────────────────────────────────────────────────────

const PROFILER_SUMMARY = {
  total_functions: 2,
  functions: {
    preprocess: {
      label: 'preprocess', n: 20, avg_ms: 12.4, min_ms: 8.1,
      max_ms: 24.5, median_ms: 11.9, p95_ms: 22.0, p99_ms: 24.0,
      throughput_rps: 80.6, timestamp: '2024-07-14T12:00:00Z',
    },
    cache_stats: {
      label: 'cache_stats', n: 50, avg_ms: 0.3, min_ms: 0.1,
      max_ms: 1.2, median_ms: 0.2, p95_ms: 0.8, p99_ms: 1.1,
      throughput_rps: 3333.0, timestamp: '2024-07-14T12:00:00Z',
    },
  },
};

const MEMORY_REPORT = {
  timestamp: '2024-07-14T12:00:00Z',
  current_rss_mb: 312.5,
  total_operations_tracked: 3,
  warning_count: 0,
  warnings: [],
  operations: [
    {
      label: 'preprocess', before_mb: 310.0, after_mb: 312.5,
      delta_mb: 2.5, elapsed_ms: 14.2, warning: false,
      timestamp: '2024-07-14T12:00:00Z',
    },
  ],
  snapshots: [],
  resource_summary: {
    ram_total_mb: 16384, ram_used_mb: 8000, ram_available_mb: 8384,
    ram_percent: 48.8, process_rss_mb: 312.5,
  },
};

const CACHE_REPORT = {
  timestamp: '2024-07-14T12:00:00Z',
  model_cache: {
    name: 'model_cache', capacity: 4, size: 1, utilization: 0.25,
    hit_rate: 0.9, total_hits: 90, total_misses: 10,
    total_evictions: 0, avg_load_ms: 250.0,
  },
  prediction_cache: {
    name: 'prediction_cache', capacity: 256, size: 12,
    hit_rate: 0.6, hits: 60, misses: 40, ttl_s: 300,
  },
  dataset_metadata_cache: {
    name: 'dataset_metadata_cache', size: 1,
    hit_rate: 0.95, hits: 19, misses: 1, ttl_s: 60,
  },
  dashboard_cache: {
    name: 'dashboard_cache', size: 3,
    hit_rate: 0.7, hits: 70, misses: 30, ttl_s: 5,
  },
  recommendations: ['Cache performing well (hit_rate=90%).'],
};

const API_STATS_REPORT = {
  timestamp: '2024-07-14T12:00:00Z',
  total_endpoints_tracked: 2,
  slow_endpoints: [],
  ranked_by_latency: [
    {
      path: '/api/v1/predict/image', method: 'POST',
      total_calls: 50, errors: 1, avg_ms: 42.0, min_ms: 15.0,
      max_ms: 280.0, median_ms: 38.0, p95_ms: 120.0, p99_ms: 240.0,
      error_rate: 0.02, rps: 0.83, is_slow: false,
      timestamp: '2024-07-14T12:00:00Z',
    },
  ],
  all_endpoints: [
    {
      path: '/api/v1/predict/image', method: 'POST',
      total_calls: 50, errors: 1, avg_ms: 42.0, min_ms: 15.0,
      max_ms: 280.0, median_ms: 38.0, p95_ms: 120.0, p99_ms: 240.0,
      error_rate: 0.02, rps: 0.83, is_slow: false,
      timestamp: '2024-07-14T12:00:00Z',
    },
  ],
};

const CONCURRENCY_REPORT = {
  timestamp: '2024-07-14T12:00:00Z',
  total_tests: 1,
  results: [
    {
      label: 'stress_w10', workers: 10, total_requests: 50,
      completed: 50, failed: 0, error_rate: 0.0,
      avg_ms: 3.2, min_ms: 0.8, max_ms: 12.4,
      median_ms: 2.9, p95_ms: 8.1, p99_ms: 11.2,
      throughput_rps: 312.5, total_elapsed_ms: 160.0,
      sample_errors: [], timestamp: '2024-07-14T12:00:00Z',
    },
  ],
};

const BENCHMARK_RESULT = {
  suite_name: 'full_suite',
  started_at: '2024-07-14T12:00:00Z',
  finished_at: '2024-07-14T12:00:45Z',
  total_ms: 45000,
  benchmark_count: 3,
  benchmarks: [
    {
      name: 'preprocessing', n: 10, avg_ms: 12.5, min_ms: 8.0,
      max_ms: 25.0, median_ms: 11.8, p95_ms: 22.0, throughput_rps: 80.0,
      total_ms: 125.0, status: 'ok', error: null,
      timestamp: '2024-07-14T12:00:00Z',
    },
    {
      name: 'cache_get_hit', n: 50, avg_ms: 0.12, min_ms: 0.05,
      max_ms: 0.8, median_ms: 0.1, p95_ms: 0.5, throughput_rps: 8333.0,
      total_ms: 6.0, status: 'ok', error: null,
      timestamp: '2024-07-14T12:00:00Z',
    },
    {
      name: 'dataset_metadata', n: 0, avg_ms: 0, min_ms: 0,
      max_ms: 0, median_ms: 0, p95_ms: 0, throughput_rps: 0,
      total_ms: 0, status: 'skipped', error: 'No processed dataset found',
      timestamp: '2024-07-14T12:00:00Z',
    },
  ],
};

const PERFORMANCE_SUMMARY = {
  report_type: 'performance',
  generated_at: '2024-07-14T12:00:00Z',
  system: { cpu_percent: 34.1, ram_used_mb: 4096, ram_percent: 50.0, process_rss_mb: 312.5, uptime_seconds: 3600, platform: 'Linux' },
  inference: { total_predictions: 142, success_rate: 0.9718, avg_latency_ms: 38.4 },
  cache: CACHE_REPORT,
  memory: MEMORY_REPORT,
  api: API_STATS_REPORT,
  profiler: PROFILER_SUMMARY,
  concurrency: CONCURRENCY_REPORT,
};

// ── getPerformanceSummary ──────────────────────────────────────────────────

describe('getPerformanceSummary', () => {
  it('returns the summary data object', async () => {
    mock.onGet('/performance/summary').reply(200, {
      success: true, data: PERFORMANCE_SUMMARY, message: 'ok',
    });
    const result = await getPerformanceSummary();
    expect(result.report_type).toBe('performance');
    expect(result.generated_at).toBe('2024-07-14T12:00:00Z');
  });

  it('includes all top-level sections', async () => {
    mock.onGet('/performance/summary').reply(200, {
      success: true, data: PERFORMANCE_SUMMARY, message: 'ok',
    });
    const result = await getPerformanceSummary();
    expect(result).toHaveProperty('system');
    expect(result).toHaveProperty('inference');
    expect(result).toHaveProperty('cache');
    expect(result).toHaveProperty('memory');
    expect(result).toHaveProperty('api');
    expect(result).toHaveProperty('profiler');
    expect(result).toHaveProperty('concurrency');
  });

  it('surfaces nested cache hit_rate', async () => {
    mock.onGet('/performance/summary').reply(200, {
      success: true, data: PERFORMANCE_SUMMARY, message: 'ok',
    });
    const result = await getPerformanceSummary();
    expect(result.cache.model_cache.hit_rate).toBe(0.9);
  });

  it('surfaces nested memory current_rss_mb', async () => {
    mock.onGet('/performance/summary').reply(200, {
      success: true, data: PERFORMANCE_SUMMARY, message: 'ok',
    });
    const result = await getPerformanceSummary();
    expect(result.memory.current_rss_mb).toBe(312.5);
  });

  it('throws on 500 error', async () => {
    mock.onGet('/performance/summary').reply(500);
    await expect(getPerformanceSummary()).rejects.toBeTruthy();
  });
});

// ── getProfilerSummary ────────────────────────────────────────────────────

describe('getProfilerSummary', () => {
  it('returns profiler summary with default top=20', async () => {
    mock.onGet('/performance/profiler?top=20').reply(200, {
      success: true, data: PROFILER_SUMMARY, message: 'ok',
    });
    const result = await getProfilerSummary();
    expect(result.total_functions).toBe(2);
    expect(Object.keys(result.functions)).toHaveLength(2);
  });

  it('uses custom top parameter', async () => {
    mock.onGet('/performance/profiler?top=50').reply(200, {
      success: true, data: PROFILER_SUMMARY, message: 'ok',
    });
    const result = await getProfilerSummary(50);
    expect(result.total_functions).toBe(2);
  });

  it('returns correct function stats', async () => {
    mock.onGet('/performance/profiler?top=20').reply(200, {
      success: true, data: PROFILER_SUMMARY, message: 'ok',
    });
    const result = await getProfilerSummary();
    const preprocess = result.functions['preprocess'];
    expect(preprocess.avg_ms).toBe(12.4);
    expect(preprocess.throughput_rps).toBe(80.6);
    expect(preprocess.n).toBe(20);
  });

  it('throws on 401 (auth required)', async () => {
    mock.onGet('/performance/profiler?top=20').reply(401);
    await expect(getProfilerSummary()).rejects.toBeTruthy();
  });
});

// ── getMemoryReport ────────────────────────────────────────────────────────

describe('getMemoryReport', () => {
  it('returns memory report with current RSS', async () => {
    mock.onGet('/performance/memory').reply(200, {
      success: true, data: MEMORY_REPORT, message: 'ok',
    });
    const result = await getMemoryReport();
    expect(result.current_rss_mb).toBe(312.5);
    expect(result.total_operations_tracked).toBe(3);
    expect(result.warning_count).toBe(0);
  });

  it('returns operations array', async () => {
    mock.onGet('/performance/memory').reply(200, {
      success: true, data: MEMORY_REPORT, message: 'ok',
    });
    const result = await getMemoryReport();
    expect(Array.isArray(result.operations)).toBe(true);
    expect(result.operations[0].label).toBe('preprocess');
    expect(result.operations[0].delta_mb).toBe(2.5);
  });

  it('returns resource_summary', async () => {
    mock.onGet('/performance/memory').reply(200, {
      success: true, data: MEMORY_REPORT, message: 'ok',
    });
    const result = await getMemoryReport();
    expect(result.resource_summary.ram_total_mb).toBe(16384);
    expect(result.resource_summary.process_rss_mb).toBe(312.5);
  });

  it('throws on 500 error', async () => {
    mock.onGet('/performance/memory').reply(500);
    await expect(getMemoryReport()).rejects.toBeTruthy();
  });
});

// ── getCacheReport ─────────────────────────────────────────────────────────

describe('getCacheReport', () => {
  it('returns cache report with all four caches', async () => {
    mock.onGet('/performance/cache').reply(200, {
      success: true, data: CACHE_REPORT, message: 'ok',
    });
    const result = await getCacheReport();
    expect(result.model_cache.name).toBe('model_cache');
    expect(result.prediction_cache.name).toBe('prediction_cache');
    expect(result.dataset_metadata_cache.name).toBe('dataset_metadata_cache');
    expect(result.dashboard_cache.name).toBe('dashboard_cache');
  });

  it('returns recommendations array', async () => {
    mock.onGet('/performance/cache').reply(200, {
      success: true, data: CACHE_REPORT, message: 'ok',
    });
    const result = await getCacheReport();
    expect(Array.isArray(result.recommendations)).toBe(true);
    expect(result.recommendations[0]).toContain('Cache performing well');
  });

  it('returns model_cache utilization and hit_rate', async () => {
    mock.onGet('/performance/cache').reply(200, {
      success: true, data: CACHE_REPORT, message: 'ok',
    });
    const result = await getCacheReport();
    expect(result.model_cache.hit_rate).toBe(0.9);
    expect(result.model_cache.capacity).toBe(4);
    expect(result.model_cache.size).toBe(1);
  });

  it('throws on network error', async () => {
    mock.onGet('/performance/cache').networkError();
    await expect(getCacheReport()).rejects.toBeTruthy();
  });
});

// ── getApiStats ────────────────────────────────────────────────────────────

describe('getApiStats', () => {
  it('returns API stats without slow_only filter', async () => {
    mock.onGet('/performance/api-stats').reply(200, {
      success: true, data: API_STATS_REPORT, message: 'ok',
    });
    const result = await getApiStats();
    expect(result.total_endpoints_tracked).toBe(2);
    expect(Array.isArray(result.all_endpoints)).toBe(true);
    expect(result.all_endpoints).toHaveLength(1);
  });

  it('passes slow_only=true query param', async () => {
    mock.onGet('/performance/api-stats?slow_only=true').reply(200, {
      success: true,
      data: { ...API_STATS_REPORT, all_endpoints: [] },
      message: 'ok',
    });
    const result = await getApiStats(true);
    expect(result.all_endpoints).toHaveLength(0);
  });

  it('returns endpoint latency stats', async () => {
    mock.onGet('/performance/api-stats').reply(200, {
      success: true, data: API_STATS_REPORT, message: 'ok',
    });
    const result = await getApiStats();
    const ep = result.all_endpoints[0];
    expect(ep.path).toBe('/api/v1/predict/image');
    expect(ep.avg_ms).toBe(42.0);
    expect(ep.is_slow).toBe(false);
    expect(ep.error_rate).toBe(0.02);
  });

  it('returns slow_endpoints array', async () => {
    mock.onGet('/performance/api-stats').reply(200, {
      success: true, data: API_STATS_REPORT, message: 'ok',
    });
    const result = await getApiStats();
    expect(Array.isArray(result.slow_endpoints)).toBe(true);
  });

  it('throws on 500 error', async () => {
    mock.onGet('/performance/api-stats').reply(500);
    await expect(getApiStats()).rejects.toBeTruthy();
  });
});

// ── getConcurrencyReport ───────────────────────────────────────────────────

describe('getConcurrencyReport', () => {
  it('returns concurrency report with test count', async () => {
    mock.onGet('/performance/concurrency').reply(200, {
      success: true, data: CONCURRENCY_REPORT, message: 'ok',
    });
    const result = await getConcurrencyReport();
    expect(result.total_tests).toBe(1);
    expect(Array.isArray(result.results)).toBe(true);
  });

  it('returns per-run throughput and error rate', async () => {
    mock.onGet('/performance/concurrency').reply(200, {
      success: true, data: CONCURRENCY_REPORT, message: 'ok',
    });
    const result = await getConcurrencyReport();
    const run = result.results[0];
    expect(run.label).toBe('stress_w10');
    expect(run.workers).toBe(10);
    expect(run.completed).toBe(50);
    expect(run.failed).toBe(0);
    expect(run.throughput_rps).toBe(312.5);
  });

  it('throws on 500 error', async () => {
    mock.onGet('/performance/concurrency').reply(500);
    await expect(getConcurrencyReport()).rejects.toBeTruthy();
  });
});

// ── runBenchmark ───────────────────────────────────────────────────────────

describe('runBenchmark', () => {
  const RUN_RESPONSE = {
    success: true,
    message: 'Benchmark suite completed. 2/3 benchmarks passed.',
    data: BENCHMARK_RESULT,
    background: false,
  };

  it('posts benchmark run request and returns result', async () => {
    mock.onPost('/performance/benchmark/run').reply(200, RUN_RESPONSE);
    const result = await runBenchmark({
      n_inference: 5, n_preprocess: 10, n_cache: 20,
      batch_sizes: [4, 8], background: false,
    });
    expect(result.success).toBe(true);
    expect(result.background).toBe(false);
    expect(result.data).not.toBeNull();
    expect(result.data?.benchmarks).toHaveLength(3);
  });

  it('returns background=true for async run', async () => {
    mock.onPost('/performance/benchmark/run').reply(200, {
      success: true,
      message: 'Benchmark suite started in background.',
      data: null,
      background: true,
    });
    const result = await runBenchmark({ background: true });
    expect(result.background).toBe(true);
    expect(result.data).toBeNull();
  });

  it('includes benchmark stats in response data', async () => {
    mock.onPost('/performance/benchmark/run').reply(200, RUN_RESPONSE);
    const result = await runBenchmark({ n_inference: 5 });
    const b0 = result.data?.benchmarks[0];
    expect(b0?.name).toBe('preprocessing');
    expect(b0?.status).toBe('ok');
    expect(b0?.avg_ms).toBe(12.5);
  });

  it('throws on 409 conflict (already running)', async () => {
    mock.onPost('/performance/benchmark/run').reply(409, {
      detail: 'A benchmark suite is already running.',
    });
    await expect(runBenchmark({})).rejects.toBeTruthy();
  });

  it('throws on 500 server error', async () => {
    mock.onPost('/performance/benchmark/run').reply(500);
    await expect(runBenchmark({})).rejects.toBeTruthy();
  });
});

// ── getBenchmarkResult ─────────────────────────────────────────────────────

describe('getBenchmarkResult', () => {
  it('returns the last benchmark result', async () => {
    mock.onGet('/performance/benchmark/result').reply(200, {
      success: true,
      message: 'Last benchmark result.',
      data: { ...BENCHMARK_RESULT, running: false },
      background: false,
    });
    const result = await getBenchmarkResult();
    expect(result.success).toBe(true);
    expect(result.data?.benchmarks).toHaveLength(3);
  });

  it('returns running=true when still in progress', async () => {
    mock.onGet('/performance/benchmark/result').reply(200, {
      success: true,
      message: 'Benchmark suite is still running.',
      data: { running: true },
      background: true,
    });
    const result = await getBenchmarkResult();
    expect(result.data?.running).toBe(true);
    expect(result.background).toBe(true);
  });

  it('throws 404 when no result available yet', async () => {
    mock.onGet('/performance/benchmark/result').reply(404, {
      detail: 'No benchmark result available.',
    });
    await expect(getBenchmarkResult()).rejects.toBeTruthy();
  });
});

// ── runSingleBenchmark ─────────────────────────────────────────────────────

describe('runSingleBenchmark', () => {
  const SINGLE_STAT = {
    name: 'preprocessing', n: 10, avg_ms: 12.5, min_ms: 8.0,
    max_ms: 25.0, median_ms: 11.8, p95_ms: 22.0, throughput_rps: 80.0,
    total_ms: 125.0, status: 'ok', error: null,
    timestamp: '2024-07-14T12:00:00Z',
  };

  it('posts single benchmark and returns stats', async () => {
    mock.onPost('/performance/benchmark/single').reply(200, {
      success: true,
      data: SINGLE_STAT,
      message: "Benchmark 'preprocessing' completed with status 'ok'.",
    });
    const result = await runSingleBenchmark({ name: 'preprocessing', n: 10 });
    expect(result.success).toBe(true);
    expect(result.data.name).toBe('preprocessing');
    expect(result.data.avg_ms).toBe(12.5);
  });

  it('returns error status for unknown benchmark', async () => {
    mock.onPost('/performance/benchmark/single').reply(200, {
      success: false,
      data: { name: 'bad_bench', status: 'error', error: "Unknown benchmark 'bad_bench'." },
      message: "Benchmark 'bad_bench' completed with status 'error'.",
    });
    const result = await runSingleBenchmark({ name: 'bad_bench', n: 3 });
    expect(result.success).toBe(false);
    expect(result.data.status).toBe('error');
  });

  it('throws on 500 server error', async () => {
    mock.onPost('/performance/benchmark/single').reply(500);
    await expect(runSingleBenchmark({ name: 'preprocessing' })).rejects.toBeTruthy();
  });
});

// ── resetProfiler ──────────────────────────────────────────────────────────

describe('resetProfiler', () => {
  it('sends DELETE and returns cleared subsystems', async () => {
    mock.onDelete('/performance/profiler/reset').reply(200, {
      success: true,
      data: { cleared: ['profiler', 'api_optimizer', 'memory_profiler'], errors: [] },
      message: 'Reset 3 subsystem(s).',
    });
    const result = await resetProfiler();
    expect(result.cleared).toContain('profiler');
    expect(result.cleared).toContain('api_optimizer');
    expect(result.cleared).toContain('memory_profiler');
    expect(result.errors).toHaveLength(0);
  });

  it('reports partial errors when a subsystem fails', async () => {
    mock.onDelete('/performance/profiler/reset').reply(200, {
      success: false,
      data: { cleared: ['profiler'], errors: ['api_optimizer: some error'] },
      message: 'Reset 1 subsystem(s). Errors: ...',
    });
    const result = await resetProfiler();
    expect(result.cleared).toHaveLength(1);
    expect(result.errors).toHaveLength(1);
  });

  it('throws on 403 (non-admin user)', async () => {
    mock.onDelete('/performance/profiler/reset').reply(403, {
      detail: 'Insufficient role.',
    });
    await expect(resetProfiler()).rejects.toBeTruthy();
  });
});

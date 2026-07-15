/**
 * src/components/PerformanceDashboard.test.tsx
 *
 * Covers:
 *   - Initial render and tab structure (accessibility)
 *   - Lazy data loading: Overview tab fetches on mount
 *   - Tab switching triggers data fetch
 *   - Loaded tab state is cached (no duplicate fetches)
 *   - Error banner shown on API failure
 *   - Refresh button re-fetches current tab
 *   - Reset button calls resetProfiler and re-fetches
 *   - OverviewPanel: KPI cards, top endpoints, recommendations
 *   - ProfilerPanel: renders table rows, empty state
 *   - CachePanel: four cache cards, hit-rate bars, recommendations
 *   - MemoryPanel: KPI cards, operations table
 *   - ApiStatsPanel: endpoint table, slow-only toggle
 *   - ConcurrencyPanel: runs table, empty state
 *   - BenchmarkPanel: run button, loading state, results table
 *   - Bundle/lazy loading: component is importable (code-split boundary)
 */

import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  render, screen, fireEvent, waitFor, within,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';
import PerformanceDashboard from './PerformanceDashboard';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => { mock.reset(); vi.clearAllMocks(); });

// ── Fixtures ───────────────────────────────────────────────────────────────

const PROFILER = {
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

const MEMORY = {
  timestamp: '2024-07-14T12:00:00Z',
  current_rss_mb: 312.5,
  total_operations_tracked: 1,
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
    ram_total_mb: 16384, ram_used_mb: 8000,
    ram_available_mb: 8384, ram_percent: 48.8, process_rss_mb: 312.5,
  },
};

const CACHE = {
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

const API_STATS = {
  timestamp: '2024-07-14T12:00:00Z',
  total_endpoints_tracked: 1,
  slow_endpoints: [],
  ranked_by_latency: [],
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

const CONCURRENCY = {
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

const SUMMARY = {
  report_type: 'performance',
  generated_at: '2024-07-14T12:00:00Z',
  system: { cpu_percent: 34.1, ram_used_mb: 4096, ram_percent: 50.0,
    process_rss_mb: 312.5, uptime_seconds: 3600, platform: 'Linux' },
  inference: { total_predictions: 142, success_rate: 0.9718, avg_latency_ms: 38.4 },
  cache: CACHE,
  memory: MEMORY,
  api: API_STATS,
  profiler: PROFILER,
  concurrency: CONCURRENCY,
};

const BENCHMARK_RUN_RESPONSE = {
  success: true,
  message: '2/3 benchmarks passed.',
  data: {
    suite_name: 'full_suite',
    started_at: '2024-07-14T12:00:00Z',
    finished_at: '2024-07-14T12:00:45Z',
    total_ms: 45000,
    benchmark_count: 2,
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
    ],
    running: false,
  },
  background: false,
};

/** Stub the summary endpoint (called on mount for Overview tab). */
function stubSummary() {
  mock.onGet('/performance/summary').reply(200, {
    success: true, data: SUMMARY, message: 'ok',
  });
}

// ── Render helpers ─────────────────────────────────────────────────────────

function renderDashboard() {
  return render(<PerformanceDashboard />);
}

// ── Dashboard structure ────────────────────────────────────────────────────

describe('PerformanceDashboard — structure', () => {
  it('renders the dashboard container', async () => {
    stubSummary();
    renderDashboard();
    expect(screen.getByTestId('performance-dashboard')).toBeInTheDocument();
  });

  it('renders all seven tab buttons', async () => {
    stubSummary();
    renderDashboard();
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(7);
  });

  it('renders the correct tab labels', async () => {
    stubSummary();
    renderDashboard();
    const labels = ['Overview', 'Profiler', 'Benchmark', 'Cache', 'Memory', 'API Stats', 'Concurrency'];
    for (const label of labels) {
      expect(screen.getByRole('tab', { name: new RegExp(label, 'i') })).toBeInTheDocument();
    }
  });

  it('Overview tab is selected by default', async () => {
    stubSummary();
    renderDashboard();
    expect(screen.getByRole('tab', { name: /overview/i })).toHaveAttribute('aria-selected', 'true');
  });

  it('renders the page heading', async () => {
    stubSummary();
    renderDashboard();
    expect(screen.getByRole('heading', { name: /performance dashboard/i })).toBeInTheDocument();
  });

  it('renders Refresh button', async () => {
    stubSummary();
    renderDashboard();
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
  });

  it('renders Reset button', async () => {
    stubSummary();
    renderDashboard();
    expect(screen.getByRole('button', { name: /reset/i })).toBeInTheDocument();
  });
});

// ── Lazy loading & Overview panel ─────────────────────────────────────────

describe('PerformanceDashboard — Overview panel', () => {
  it('fetches summary on mount and shows KPI cards', async () => {
    stubSummary();
    renderDashboard();
    // KPI: Process RSS
    await waitFor(() => expect(screen.getByText(/313 MB|312 MB/)).toBeInTheDocument());
  });

  it('shows model cache hit rate KPI', async () => {
    stubSummary();
    renderDashboard();
    await waitFor(() => expect(screen.getByText('90%')).toBeInTheDocument());
  });

  it('shows slow endpoints count as 0', async () => {
    stubSummary();
    renderDashboard();
    await waitFor(() => {
      // KPI card for "Slow Endpoints" with value "0"
      const labels = screen.getAllByText('0');
      expect(labels.length).toBeGreaterThan(0);
    });
  });

  it('shows cache recommendations', async () => {
    stubSummary();
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/Cache performing well/i)).toBeInTheDocument(),
    );
  });

  it('shows top endpoints table when api data has ranked results', async () => {
    mock.onGet('/performance/summary').reply(200, {
      success: true,
      data: {
        ...SUMMARY,
        api: {
          ...API_STATS,
          ranked_by_latency: API_STATS.all_endpoints,
        },
      },
      message: 'ok',
    });
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/Top Endpoints by Latency/i)).toBeInTheDocument(),
    );
  });

  it('shows updated timestamp after load', async () => {
    stubSummary();
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/updated/i)).toBeInTheDocument(),
    );
  });
});

// ── Error handling ─────────────────────────────────────────────────────────

describe('PerformanceDashboard — error handling', () => {
  it('shows error banner on API failure', async () => {
    mock.onGet('/performance/summary').reply(500);
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument(),
    );
  });

  it('shows error banner on network error', async () => {
    mock.onGet('/performance/summary').networkError();
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument(),
    );
  });
});

// ── Tab switching ──────────────────────────────────────────────────────────

describe('PerformanceDashboard — tab switching', () => {
  it('clicking Profiler tab fetches profiler data', async () => {
    stubSummary();
    mock.onGet('/performance/profiler?top=50').reply(200, {
      success: true, data: PROFILER, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    fireEvent.click(screen.getByRole('tab', { name: /profiler/i }));
    await waitFor(() =>
      expect(screen.getByText('preprocess')).toBeInTheDocument(),
    );
  });

  it('clicking Cache tab fetches cache report', async () => {
    stubSummary();
    mock.onGet('/performance/cache').reply(200, {
      success: true, data: CACHE, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    fireEvent.click(screen.getByRole('tab', { name: /cache/i }));
    await waitFor(() =>
      expect(screen.getByText(/model cache/i)).toBeInTheDocument(),
    );
  });

  it('clicking Memory tab fetches memory report', async () => {
    stubSummary();
    mock.onGet('/performance/memory').reply(200, {
      success: true, data: MEMORY, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    fireEvent.click(screen.getByRole('tab', { name: /memory/i }));
    await waitFor(() =>
      expect(screen.getByText(/process rss/i)).toBeInTheDocument(),
    );
  });

  it('clicking API Stats tab fetches api-stats', async () => {
    stubSummary();
    mock.onGet('/performance/api-stats').reply(200, {
      success: true, data: API_STATS, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    fireEvent.click(screen.getByRole('tab', { name: /api stats/i }));
    await waitFor(() =>
      expect(screen.getByText('/api/v1/predict/image')).toBeInTheDocument(),
    );
  });

  it('clicking Concurrency tab fetches concurrency report', async () => {
    stubSummary();
    mock.onGet('/performance/concurrency').reply(200, {
      success: true, data: CONCURRENCY, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    fireEvent.click(screen.getByRole('tab', { name: /concurrency/i }));
    await waitFor(() =>
      expect(screen.getByText('stress_w10')).toBeInTheDocument(),
    );
  });

  it('clicking Benchmark tab shows run button without a fetch', async () => {
    stubSummary();
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    fireEvent.click(screen.getByRole('tab', { name: /benchmark/i }));
    expect(screen.getByRole('button', { name: /run benchmark/i })).toBeInTheDocument();
  });

  it('selected tab has aria-selected=true', async () => {
    stubSummary();
    mock.onGet('/performance/cache').reply(200, {
      success: true, data: CACHE, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    fireEvent.click(screen.getByRole('tab', { name: /cache/i }));
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /cache/i }))
        .toHaveAttribute('aria-selected', 'true'),
    );
    expect(screen.getByRole('tab', { name: /overview/i }))
      .toHaveAttribute('aria-selected', 'false');
  });
});

// ── Tab data caching (no duplicate fetches) ────────────────────────────────

describe('PerformanceDashboard — tab caching', () => {
  it('does not re-fetch Overview when switching back', async () => {
    stubSummary();
    mock.onGet('/performance/cache').reply(200, {
      success: true, data: CACHE, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    // Switch to Cache then back to Overview
    fireEvent.click(screen.getByRole('tab', { name: /cache/i }));
    await waitFor(() => screen.getByText(/model cache/i));
    fireEvent.click(screen.getByRole('tab', { name: /overview/i }));

    // Summary was only called once (on mount)
    const summaryCalls = mock.history.get.filter(
      (r) => r.url === '/performance/summary',
    );
    expect(summaryCalls).toHaveLength(1);
  });
});

// ── Refresh button ─────────────────────────────────────────────────────────

describe('PerformanceDashboard — refresh', () => {
  it('clicking Refresh re-fetches the active tab', async () => {
    stubSummary();
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    // First fetch happened on mount — stub another call
    mock.onGet('/performance/summary').reply(200, {
      success: true, data: SUMMARY, message: 'ok',
    });
    fireEvent.click(screen.getByRole('button', { name: /refresh/i }));

    await waitFor(() => {
      const calls = mock.history.get.filter(
        (r) => r.url === '/performance/summary',
      );
      expect(calls.length).toBeGreaterThanOrEqual(2);
    });
  });
});

// ── Reset button ───────────────────────────────────────────────────────────

describe('PerformanceDashboard — reset', () => {
  it('clicking Reset calls DELETE profiler/reset', async () => {
    stubSummary();
    mock.onDelete('/performance/profiler/reset').reply(200, {
      success: true,
      data: { cleared: ['profiler', 'api_optimizer', 'memory_profiler'], errors: [] },
      message: 'Reset 3 subsystem(s).',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));

    fireEvent.click(screen.getByRole('button', { name: /reset/i }));
    await waitFor(() => {
      expect(mock.history.delete).toHaveLength(1);
      expect(mock.history.delete[0].url).toBe('/performance/profiler/reset');
    });
  });
});

// ── Profiler panel ─────────────────────────────────────────────────────────

describe('PerformanceDashboard — ProfilerPanel', () => {
  async function openProfiler() {
    stubSummary();
    mock.onGet('/performance/profiler?top=50').reply(200, {
      success: true, data: PROFILER, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));
    fireEvent.click(screen.getByRole('tab', { name: /profiler/i }));
    await waitFor(() => screen.getByText('preprocess'));
  }

  it('shows function rows in profiler table', async () => {
    await openProfiler();
    expect(screen.getByText('preprocess')).toBeInTheDocument();
    expect(screen.getByText('cache_stats')).toBeInTheDocument();
  });

  it('shows tracked function count', async () => {
    await openProfiler();
    expect(screen.getByText(/2 function\(s\) tracked/i)).toBeInTheDocument();
  });

  it('shows empty state when no data', async () => {
    stubSummary();
    mock.onGet('/performance/profiler?top=50').reply(200, {
      success: true,
      data: { total_functions: 0, functions: {} },
      message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));
    fireEvent.click(screen.getByRole('tab', { name: /profiler/i }));
    await waitFor(() =>
      expect(screen.getByText(/no profiling data/i)).toBeInTheDocument(),
    );
  });

  it('profiler table has accessible aria-label', async () => {
    await openProfiler();
    expect(screen.getByRole('table', { name: /profiler results/i })).toBeInTheDocument();
  });
});

// ── Cache panel ────────────────────────────────────────────────────────────

describe('PerformanceDashboard — CachePanel', () => {
  async function openCache() {
    stubSummary();
    mock.onGet('/performance/cache').reply(200, {
      success: true, data: CACHE, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));
    fireEvent.click(screen.getByRole('tab', { name: /cache/i }));
    await waitFor(() => screen.getByText(/model cache/i));
  }

  it('shows all four cache cards', async () => {
    await openCache();
    expect(screen.getByText(/model cache/i)).toBeInTheDocument();
    expect(screen.getByText(/prediction cache/i)).toBeInTheDocument();
    expect(screen.getByText(/dataset metadata cache/i)).toBeInTheDocument();
    expect(screen.getByText(/dashboard cache/i)).toBeInTheDocument();
  });

  it('shows hit rates in cache cards', async () => {
    await openCache();
    // 90% for model_cache
    expect(screen.getByText('90%')).toBeInTheDocument();
  });

  it('shows cache recommendations', async () => {
    await openCache();
    expect(screen.getByText(/Cache performing well/i)).toBeInTheDocument();
  });

  it('shows entry counts', async () => {
    await openCache();
    // "1 / 4 entries" for model_cache
    expect(screen.getByText(/1 \/ 4 entries/)).toBeInTheDocument();
  });
});

// ── Memory panel ───────────────────────────────────────────────────────────

describe('PerformanceDashboard — MemoryPanel', () => {
  async function openMemory() {
    stubSummary();
    mock.onGet('/performance/memory').reply(200, {
      success: true, data: MEMORY, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));
    fireEvent.click(screen.getByRole('tab', { name: /memory/i }));
    await waitFor(() => screen.getByText(/process rss/i));
  }

  it('shows Process RSS KPI', async () => {
    await openMemory();
    expect(screen.getByText(/313 MB|312 MB/)).toBeInTheDocument();
  });

  it('shows ops tracked and warnings', async () => {
    await openMemory();
    // "1" for total_operations_tracked, "0" for warnings
    expect(screen.getByText('Ops Tracked')).toBeInTheDocument();
  });

  it('shows recent memory deltas table', async () => {
    await openMemory();
    expect(screen.getByRole('table', { name: /memory operation deltas/i })).toBeInTheDocument();
    expect(screen.getByText('preprocess')).toBeInTheDocument();
  });

  it('shows delta value in ops table', async () => {
    await openMemory();
    // delta_mb = 2.5 → rendered as "+2.5"
    expect(screen.getByText(/\+2\.5/)).toBeInTheDocument();
  });
});

// ── API Stats panel ────────────────────────────────────────────────────────

describe('PerformanceDashboard — ApiStatsPanel', () => {
  async function openApiStats() {
    stubSummary();
    mock.onGet('/performance/api-stats').reply(200, {
      success: true, data: API_STATS, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));
    fireEvent.click(screen.getByRole('tab', { name: /api stats/i }));
    await waitFor(() => screen.getByText('/api/v1/predict/image'));
  }

  it('shows endpoint table with correct path', async () => {
    await openApiStats();
    expect(screen.getByText('/api/v1/predict/image')).toBeInTheDocument();
  });

  it('shows endpoint table with accessible aria-label', async () => {
    await openApiStats();
    expect(
      screen.getByRole('table', { name: /api endpoint statistics/i }),
    ).toBeInTheDocument();
  });

  it('shows tracked endpoint count', async () => {
    await openApiStats();
    expect(screen.getByText(/1 endpoint\(s\)/i)).toBeInTheDocument();
  });

  it('shows slow count as 0', async () => {
    await openApiStats();
    expect(screen.getByText(/0 slow/i)).toBeInTheDocument();
  });

  it('has slow-only checkbox', async () => {
    await openApiStats();
    expect(
      screen.getByRole('checkbox', { name: /slow endpoints only/i }),
    ).toBeInTheDocument();
  });

  it('toggling slow-only hides non-slow endpoints', async () => {
    await openApiStats();
    const checkbox = screen.getByRole('checkbox', { name: /slow endpoints only/i });
    fireEvent.click(checkbox);
    // /api/v1/predict/image is not slow → should disappear
    await waitFor(() =>
      expect(screen.queryByText('/api/v1/predict/image')).not.toBeInTheDocument(),
    );
    expect(screen.getByText(/no slow endpoints/i)).toBeInTheDocument();
  });
});

// ── Concurrency panel ──────────────────────────────────────────────────────

describe('PerformanceDashboard — ConcurrencyPanel', () => {
  it('shows stress test run rows', async () => {
    stubSummary();
    mock.onGet('/performance/concurrency').reply(200, {
      success: true, data: CONCURRENCY, message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));
    fireEvent.click(screen.getByRole('tab', { name: /concurrency/i }));
    await waitFor(() => screen.getByText('stress_w10'));
    expect(
      screen.getByRole('table', { name: /concurrency test results/i }),
    ).toBeInTheDocument();
  });

  it('shows empty state message when no tests run', async () => {
    stubSummary();
    mock.onGet('/performance/concurrency').reply(200, {
      success: true,
      data: { timestamp: '2024-07-14T12:00:00Z', total_tests: 0, results: [] },
      message: 'ok',
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));
    fireEvent.click(screen.getByRole('tab', { name: /concurrency/i }));
    await waitFor(() =>
      expect(screen.getByText(/no concurrency tests run yet/i)).toBeInTheDocument(),
    );
  });
});

// ── Benchmark panel ────────────────────────────────────────────────────────

describe('PerformanceDashboard — BenchmarkPanel', () => {
  async function openBenchmark() {
    stubSummary();
    renderDashboard();
    await waitFor(() => screen.getByTestId('performance-dashboard'));
    fireEvent.click(screen.getByRole('tab', { name: /benchmark/i }));
  }

  it('shows Run Benchmark button when no result', async () => {
    await openBenchmark();
    expect(
      screen.getByRole('button', { name: /run benchmark suite/i }),
    ).toBeInTheDocument();
  });

  it('disables the run button while benchmark is running', async () => {
    mock.onPost('/performance/benchmark/run').reply(200, {
      success: true, message: 'started', data: null, background: true,
    });
    // Poll returns running=true
    mock.onGet('/performance/benchmark/result').reply(200, {
      success: true, message: 'still running',
      data: { running: true }, background: true,
    });

    await openBenchmark();
    const btn = screen.getByRole('button', { name: /run benchmark suite/i });
    fireEvent.click(btn);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /running/i })).toBeDisabled(),
    );
  });

  it('shows results table after inline run completes', async () => {
    mock.onPost('/performance/benchmark/run').reply(200, BENCHMARK_RUN_RESPONSE);

    await openBenchmark();
    fireEvent.click(screen.getByRole('button', { name: /run benchmark suite/i }));
    await waitFor(() =>
      expect(screen.getByRole('table', { name: /benchmark results/i })).toBeInTheDocument(),
    );
    expect(screen.getByText('preprocessing')).toBeInTheDocument();
    expect(screen.getByText('cache_get_hit')).toBeInTheDocument();
  });

  it('shows status badges for each benchmark', async () => {
    mock.onPost('/performance/benchmark/run').reply(200, BENCHMARK_RUN_RESPONSE);

    await openBenchmark();
    fireEvent.click(screen.getByRole('button', { name: /run benchmark suite/i }));
    await waitFor(() => screen.getByRole('table', { name: /benchmark results/i }));

    const okBadges = screen.getAllByText('ok');
    expect(okBadges.length).toBeGreaterThanOrEqual(2);
  });

  it('shows error banner when run fails', async () => {
    mock.onPost('/performance/benchmark/run').reply(409, {
      detail: 'A benchmark suite is already running.',
    });

    await openBenchmark();
    fireEvent.click(screen.getByRole('button', { name: /run benchmark suite/i }));
    await waitFor(() =>
      expect(screen.getByText(/failed|error/i)).toBeInTheDocument(),
    );
  });

  it('shows total run time after completion', async () => {
    mock.onPost('/performance/benchmark/run').reply(200, BENCHMARK_RUN_RESPONSE);

    await openBenchmark();
    fireEvent.click(screen.getByRole('button', { name: /run benchmark suite/i }));
    await waitFor(() =>
      // total_ms = 45000 → 45.0s
      expect(screen.getByText(/45\.0s total/i)).toBeInTheDocument(),
    );
  });
});

// ── Lazy loading / code split ──────────────────────────────────────────────

describe('PerformanceDashboard — lazy loading / import', () => {
  it('is importable as a default export (code-split boundary check)', async () => {
    const mod = await import('./PerformanceDashboard');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  it('renders without crashing when all API calls succeed', async () => {
    stubSummary();
    const { container } = renderDashboard();
    expect(container).toBeTruthy();
    await waitFor(() =>
      expect(screen.getByTestId('performance-dashboard')).toBeInTheDocument(),
    );
  });
});

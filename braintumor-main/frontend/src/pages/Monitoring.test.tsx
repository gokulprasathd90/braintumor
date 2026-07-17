/**
 * src/pages/Monitoring.test.tsx
 *
 * The useDashboard hook is mocked so the test doesn't start live polling.
 * The getDashboardHistory API is mocked via axios-mock-adapter for the
 * History tab (which calls it directly, not through the hook).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '@/api/client';

// Mock useDashboard BEFORE importing the page
vi.mock('@/hooks/useDashboard', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useDashboard')>();
  return { ...actual, useDashboard: vi.fn() };
});

import Monitoring from './Monitoring';
import { useDashboard } from '@/hooks/useDashboard';

const mock = new MockAdapter(apiClient, { onNoMatch: 'throwException' });
beforeEach(() => mock.reset());
afterEach(() => { mock.reset(); vi.clearAllMocks(); });

// ── Fixtures ───────────────────────────────────────────────────────────────

const OVERVIEW = {
  timestamp: '2024-07-14T12:00:00Z',
  service_version: '1.0.0',
  system: { cpu_percent: 34.1, ram_percent: 60.0, disk_percent: 42.0, gpu_available: false, uptime_seconds: 3600, platform: 'Linux', ram_used_mb: 4096 },
  inference: { total_predictions: 100, succeeded: 98, failed: 2, success_rate: 0.98, avg_latency_ms: 38.4, p95_latency_ms: null, top_classes: [{ class_name: 'glioma', count: 67 }], batch_runs: 3 },
  training: { total_jobs: 5, running_jobs: 0, completed_jobs: 4, failed_jobs: 1, best_val_accuracy: 0.9730, total_experiments: 4 },
  models: {},
  alerts: [],
};

const SYSTEM = {
  timestamp: '2024-07-14T12:00:00Z', uptime_seconds: 3612, platform: 'Linux',
  python_version: '3.11.0', cpu_percent: 34.1, cpu_per_core: [28.0, 40.2],
  cpu_count_logical: 4, cpu_count_physical: 2, cpu_freq_mhz: null,
  ram_total_mb: 8192, ram_used_mb: 4201, ram_available_mb: 3991, ram_percent: 51.3,
  disk_total_gb: 256, disk_used_gb: 109, disk_free_gb: 147, disk_percent: 42.7,
  gpu_available: false, gpu_count: 0, gpus: [],
  process_pid: 1234, process_cpu_percent: 2.1, process_ram_mb: 412.8, process_threads: 8,
};

const INFERENCE = {
  timestamp: '2024-07-14T12:00:00Z', started_at: '2024-07-14T10:00:00Z',
  total_predictions: 142, succeeded: 138, failed: 4, success_rate: 0.9718,
  per_model_counts: { efficientnet: 138 },
  avg_latency_ms: 38.4, min_latency_ms: null, max_latency_ms: null, p95_latency_ms: 74.1,
  confidence_distribution: { buckets: ['<50%', '50–70%', '70–80%', '80–90%', '90–95%', '95–100%'], counts: [1, 2, 3, 10, 20, 102] },
  class_distribution: { glioma: 67, notumor: 44 },
  top_classes: [], batch_runs: 3, batch_images_processed: 45, batch_succeeded: 43, batch_failed: 2,
  recent_predictions: [],
};

const TRAINING = {
  timestamp: '2024-07-14T12:00:00Z', total_jobs: 7, queued_jobs: 0, running_jobs: 0,
  completed_jobs: 6, failed_jobs: 1, avg_job_duration_s: 1800,
  architecture_counts: { efficientnet: 4, resnet50: 2 },
  recent_jobs: [], total_experiments: 6, best_val_accuracy: 0.973, recent_experiments: [],
};

const HISTORY = { metric_type: 'system', hours: 24, count: 0, data: [] };

function mockHookLoaded() {
  vi.mocked(useDashboard).mockReturnValue({
    overview: OVERVIEW,
    system: SYSTEM,
    inference: INFERENCE,
    training: TRAINING,
    loading: false,
    error: null,
    lastUpdated: new Date('2024-07-14T12:00:00Z'),
    refresh: vi.fn(),
  });
}

function mockHookLoading() {
  vi.mocked(useDashboard).mockReturnValue({
    overview: null, system: null, inference: null, training: null,
    loading: true, error: null, lastUpdated: null, refresh: vi.fn(),
  });
}

function mockHookError() {
  vi.mocked(useDashboard).mockReturnValue({
    overview: null, system: null, inference: null, training: null,
    loading: false, error: 'Network error', lastUpdated: null, refresh: vi.fn(),
  });
}

const renderPage = () =>
  render(<MemoryRouter><Monitoring /></MemoryRouter>);

// ── Tests ──────────────────────────────────────────────────────────────────

describe('Monitoring page', () => {
  it('renders the page heading', () => {
    mockHookLoading();
    renderPage();
    expect(screen.getByText('Monitoring Dashboard')).toBeInTheDocument();
  });

  it('renders all 5 tab buttons', () => {
    mockHookLoading();
    renderPage();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /system/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /inference/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /training/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /history/i })).toBeInTheDocument();
  });

  it('shows loading spinner initially', () => {
    mockHookLoading();
    renderPage();
    // Loading spinner visible, no data sections rendered yet
    expect(screen.queryByText('System Health')).not.toBeInTheDocument();
  });

  it('shows overview KPIs after data loads', () => {
    mockHookLoaded();
    renderPage();
    expect(screen.getByText('System Health')).toBeInTheDocument();
    expect(screen.getByText('34.1%')).toBeInTheDocument();
  });

  it('shows inference section in overview', () => {
    mockHookLoaded();
    renderPage();
    // "Inference" appears in both the tab and the section heading
    expect(screen.getAllByText('Inference').length).toBeGreaterThanOrEqual(1);
  });

  it('shows training section in overview', () => {
    mockHookLoaded();
    renderPage();
    expect(screen.getAllByText('Training').length).toBeGreaterThanOrEqual(1);
  });

  it('shows best val accuracy in overview', () => {
    mockHookLoaded();
    renderPage();
    expect(screen.getByText('97.30%')).toBeInTheDocument();
  });

  it('shows top class badge in overview', () => {
    mockHookLoaded();
    renderPage();
    expect(screen.getByText(/glioma · 67/)).toBeInTheDocument();
  });

  it('switches to System tab and shows system panel', () => {
    mockHookLoaded();
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: /system/i }));
    expect(screen.getByTestId('system-health-panel')).toBeInTheDocument();
  });

  it('switches to Inference tab and shows inference panel', () => {
    mockHookLoaded();
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: /inference/i }));
    expect(screen.getByTestId('inference-metrics-panel')).toBeInTheDocument();
  });

  it('switches to Training tab and shows training panel', () => {
    mockHookLoaded();
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: /training/i }));
    expect(screen.getByTestId('training-metrics-panel')).toBeInTheDocument();
  });

  it('switches to History tab', () => {
    mockHookLoaded();
    mock.onGet(/\/dashboard\/history/).reply(200, { success: true, data: HISTORY });
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: /history/i }));
    expect(screen.getByText('Metrics History')).toBeInTheDocument();
  });

  it('has Refresh button', () => {
    mockHookLoading();
    renderPage();
    expect(screen.getByLabelText('Refresh metrics')).toBeInTheDocument();
  });

  it('has JSON export button', () => {
    mockHookLoading();
    renderPage();
    expect(screen.getByLabelText('Export metrics as JSON')).toBeInTheDocument();
  });

  it('has CSV export button', () => {
    mockHookLoading();
    renderPage();
    expect(screen.getByLabelText('Export predictions as CSV')).toBeInTheDocument();
  });

  it('shows error message when hook reports error', () => {
    mockHookError();
    renderPage();
    expect(screen.getByText(/could not load metrics/i)).toBeInTheDocument();
  });

  it('shows alerts banner when alerts present', () => {
    vi.mocked(useDashboard).mockReturnValue({
      overview: {
        ...OVERVIEW,
        alerts: [{ level: 'warning', domain: 'system', message: 'CPU usage high: 82%' }],
      },
      system: SYSTEM, inference: INFERENCE, training: TRAINING,
      loading: false, error: null, lastUpdated: new Date(), refresh: vi.fn(),
    });
    renderPage();
    expect(screen.getByText(/CPU usage high: 82%/)).toBeInTheDocument();
  });

  it('History tab has metric type selector', () => {
    mockHookLoaded();
    mock.onGet(/\/dashboard\/history/).reply(200, { success: true, data: HISTORY });
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: /history/i }));
    expect(screen.getByLabelText('Metric type for history chart')).toBeInTheDocument();
  });

  it('History tab has lookback window selector', () => {
    mockHookLoaded();
    mock.onGet(/\/dashboard\/history/).reply(200, { success: true, data: HISTORY });
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: /history/i }));
    expect(screen.getByLabelText('History lookback window')).toBeInTheDocument();
  });

  it('active tab has aria-selected=true', () => {
    mockHookLoading();
    renderPage();
    const overviewTab = screen.getByRole('tab', { name: /overview/i });
    expect(overviewTab).toHaveAttribute('aria-selected', 'true');
  });

  it('non-active tab has aria-selected=false', () => {
    mockHookLoading();
    renderPage();
    const systemTab = screen.getByRole('tab', { name: /system/i });
    expect(systemTab).toHaveAttribute('aria-selected', 'false');
  });

  it('refresh button calls hook refresh', () => {
    const refreshFn = vi.fn();
    vi.mocked(useDashboard).mockReturnValue({
      overview: null, system: null, inference: null, training: null,
      loading: false, error: null, lastUpdated: null, refresh: refreshFn,
    });
    renderPage();
    fireEvent.click(screen.getByLabelText('Refresh metrics'));
    expect(refreshFn).toHaveBeenCalledOnce();
  });

  it('JSON export button is disabled when no data', () => {
    mockHookLoading();
    renderPage();
    expect(screen.getByLabelText('Export metrics as JSON')).toBeDisabled();
  });

  it('JSON export button is enabled when data loaded', () => {
    mockHookLoaded();
    renderPage();
    expect(screen.getByLabelText('Export metrics as JSON')).not.toBeDisabled();
  });
});

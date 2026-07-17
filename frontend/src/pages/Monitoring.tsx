/**
 * Monitoring — full metrics & monitoring dashboard.
 *
 * Tabs:
 *   Overview   — composite alerts + key KPIs
 *   System     — CPU/RAM/disk/GPU gauges + history chart
 *   Inference  — prediction stats, confidence dist, class dist
 *   Training   — job counts, arch chart, recent experiments
 *   History    — configurable rolling time-series chart
 */

import { useState, useCallback } from 'react';
import Layout from '@/components/Layout';
import LoadingSpinner from '@/components/LoadingSpinner';
import AlertsBanner from '@/components/AlertsBanner';
import SystemHealthPanel from '@/components/SystemHealthPanel';
import InferenceMetricsPanel from '@/components/InferenceMetricsPanel';
import TrainingMetricsPanel from '@/components/TrainingMetricsPanel';
import MetricsHistoryChart from '@/components/MetricsHistoryChart';
import { useDashboard } from '@/hooks/useDashboard';
import { getDashboardHistory, type HistoryMetricType } from '@/api/dashboard';
import { exportMetricsJson, exportMetricsCsv } from '@/utils/metricsExport';
import type { DashboardHistoryPoint } from '@/types';

// ── Tab definitions ────────────────────────────────────────────────────────

type Tab = 'overview' | 'system' | 'inference' | 'training' | 'history';

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'overview',  label: 'Overview',  icon: '📊' },
  { id: 'system',    label: 'System',    icon: '🖥️' },
  { id: 'inference', label: 'Inference', icon: '🧠' },
  { id: 'training',  label: 'Training',  icon: '🏋️' },
  { id: 'history',   label: 'History',   icon: '📈' },
];

// ── History chart metric config per type ──────────────────────────────────

const HISTORY_METRIC_LINES: Record<HistoryMetricType, import('@/components/MetricsHistoryChart').MetricLine[]> = {
  system: [
    { key: 'cpu_percent',  label: 'CPU %',  color: '#3b82f6', format: (v) => `${v}%` },
    { key: 'ram_percent',  label: 'RAM %',  color: '#8b5cf6', format: (v) => `${v}%` },
    { key: 'disk_percent', label: 'Disk %', color: '#f59e0b', format: (v) => `${v}%` },
  ],
  inference: [
    { key: 'total_predictions', label: 'Predictions', color: '#3b82f6' },
    { key: 'avg_latency_ms',    label: 'Avg Latency (ms)', color: '#f59e0b', format: (v) => `${v} ms` },
    { key: 'success_rate',      label: 'Success Rate', color: '#22c55e', format: (v) => `${(v * 100).toFixed(1)}%` },
  ],
  training: [
    { key: 'total_jobs',     label: 'Total Jobs',     color: '#8b5cf6' },
    { key: 'running_jobs',   label: 'Running Jobs',   color: '#3b82f6' },
    { key: 'completed_jobs', label: 'Completed Jobs', color: '#22c55e' },
  ],
  overview: [
    { key: 'system.cpu_percent',          label: 'CPU %',          color: '#3b82f6', format: (v) => `${v}%` },
    { key: 'inference.total_predictions', label: 'Predictions',    color: '#22c55e' },
    { key: 'training.running_jobs',       label: 'Running Jobs',   color: '#8b5cf6' },
  ],
};

// ── KPI card ──────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
  colour = 'text-pipeline-800',
}: {
  label: string;
  value: string;
  sub?: string;
  colour?: string;
}) {
  return (
    <div className="bg-pipeline-50 rounded-xl px-4 py-4 border border-pipeline-100">
      <p className="text-xs text-pipeline-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colour}`}>{value}</p>
      {sub && <p className="text-xs text-pipeline-400 mt-1">{sub}</p>}
    </div>
  );
}

// ── Last-updated badge ────────────────────────────────────────────────────

function LastUpdated({
  lastUpdated,
  onRefresh,
}: {
  lastUpdated: Date | null;
  onRefresh: () => void;
}) {
  return (
    <div className="flex items-center gap-3 text-xs text-pipeline-400">
      {lastUpdated && (
        <span>
          Updated {lastUpdated.toLocaleTimeString()}
        </span>
      )}
      <button
        onClick={onRefresh}
        className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
        aria-label="Refresh metrics"
      >
        ↻ Refresh
      </button>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

export default function Monitoring() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  // History tab state
  const [historyType, setHistoryType] = useState<HistoryMetricType>('system');
  const [historyHours, setHistoryHours] = useState(24);
  const [historyData, setHistoryData] = useState<DashboardHistoryPoint[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const {
    overview,
    system,
    inference,
    training,
    loading,
    error,
    lastUpdated,
    refresh,
  } = useDashboard({ pollInterval: 5_000 });

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const result = await getDashboardHistory({
        metric_type: historyType,
        hours: historyHours,
      });
      setHistoryData(result.data);
    } catch {
      setHistoryData([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [historyType, historyHours]);

  // Load history when the tab is activated
  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    if (tab === 'history') fetchHistory();
  };

  // ── Export handlers ─────────────────────────────────────────────────────
  const handleExportJson = () => {
    const payload = { overview, system, inference, training };
    exportMetricsJson(payload, `metrics_${new Date().toISOString().slice(0, 10)}.json`);
  };

  const handleExportCsv = () => {
    if (!inference) return;
    exportMetricsCsv(inference.recent_predictions, `predictions_${new Date().toISOString().slice(0, 10)}.csv`);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <Layout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-pipeline-900">Monitoring Dashboard</h1>
            <p className="text-pipeline-500 mt-1 text-sm">
              Live system health, inference analytics, and training metrics.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <LastUpdated lastUpdated={lastUpdated} onRefresh={refresh} />
            <button
              onClick={handleExportJson}
              disabled={!overview}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-pipeline-200 text-pipeline-600 hover:bg-pipeline-50 disabled:opacity-40 transition-colors"
              aria-label="Export metrics as JSON"
            >
              ⬇ JSON
            </button>
            <button
              onClick={handleExportCsv}
              disabled={!inference || inference.recent_predictions.length === 0}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-pipeline-200 text-pipeline-600 hover:bg-pipeline-50 disabled:opacity-40 transition-colors"
              aria-label="Export predictions as CSV"
            >
              ⬇ CSV
            </button>
          </div>
        </div>

        {/* Global error */}
        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            Could not load metrics: {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex overflow-x-auto gap-1 border-b border-pipeline-100 pb-px" role="tablist">
          {TABS.map(({ id, label, icon }) => (
            <button
              key={id}
              role="tab"
              aria-selected={activeTab === id}
              onClick={() => handleTabChange(id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium whitespace-nowrap rounded-t-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500
                ${activeTab === id
                  ? 'bg-white border border-b-white border-pipeline-100 text-blue-700 -mb-px'
                  : 'text-pipeline-500 hover:text-pipeline-800 hover:bg-pipeline-50'
                }`}
            >
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="min-h-[400px]">
          {loading && !overview && (
            <div className="card">
              <LoadingSpinner variant="card" message="Loading metrics…" />
            </div>
          )}

          {/* ── Overview tab ─────────────────────────────────────────────── */}
          {activeTab === 'overview' && overview && (
            <div className="space-y-6">
              {/* Alerts */}
              {overview.alerts.length > 0 && (
                <AlertsBanner alerts={overview.alerts} />
              )}

              {/* System KPIs */}
              <section className="card space-y-4">
                <h2 className="section-title">System Health</h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <KpiCard
                    label="CPU"
                    value={overview.system.cpu_percent !== null ? `${overview.system.cpu_percent}%` : '—'}
                    colour={
                      (overview.system.cpu_percent ?? 0) >= 90 ? 'text-red-700' :
                      (overview.system.cpu_percent ?? 0) >= 70 ? 'text-amber-700' :
                      'text-green-700'
                    }
                  />
                  <KpiCard
                    label="RAM"
                    value={overview.system.ram_percent !== null ? `${overview.system.ram_percent}%` : '—'}
                    sub={overview.system.ram_used_mb !== null ? `${(overview.system.ram_used_mb / 1024).toFixed(1)} GB used` : undefined}
                    colour={
                      (overview.system.ram_percent ?? 0) >= 90 ? 'text-red-700' :
                      (overview.system.ram_percent ?? 0) >= 80 ? 'text-amber-700' :
                      'text-green-700'
                    }
                  />
                  <KpiCard
                    label="Disk"
                    value={overview.system.disk_percent !== null ? `${overview.system.disk_percent}%` : '—'}
                    colour={
                      (overview.system.disk_percent ?? 0) >= 90 ? 'text-red-700' :
                      (overview.system.disk_percent ?? 0) >= 80 ? 'text-amber-700' :
                      'text-pipeline-800'
                    }
                  />
                  <KpiCard
                    label="GPU"
                    value={overview.system.gpu_available ? 'Available' : 'None'}
                    colour={overview.system.gpu_available ? 'text-green-700' : 'text-pipeline-500'}
                  />
                </div>
              </section>

              {/* Inference KPIs */}
              <section className="card space-y-4">
                <h2 className="section-title">Inference</h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <KpiCard label="Predictions" value={String(overview.inference.total_predictions)} />
                  <KpiCard
                    label="Success Rate"
                    value={`${(overview.inference.success_rate * 100).toFixed(1)}%`}
                    colour={
                      overview.inference.success_rate < 0.8 ? 'text-red-700' :
                      overview.inference.success_rate < 0.95 ? 'text-amber-700' :
                      'text-green-700'
                    }
                  />
                  <KpiCard
                    label="Avg Latency"
                    value={overview.inference.avg_latency_ms !== null
                      ? `${overview.inference.avg_latency_ms.toFixed(1)} ms`
                      : '—'}
                  />
                  <KpiCard label="Batch Runs" value={String(overview.inference.batch_runs)} />
                </div>
                {overview.inference.top_classes.length > 0 && (
                  <div>
                    <p className="text-xs text-pipeline-400 mb-2">Top Predicted Classes</p>
                    <div className="flex flex-wrap gap-2">
                      {overview.inference.top_classes.map((tc) => (
                        <span key={tc.class_name} className="text-xs font-medium px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100 capitalize">
                          {tc.class_name} · {tc.count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </section>

              {/* Training KPIs */}
              <section className="card space-y-4">
                <h2 className="section-title">Training</h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <KpiCard label="Total Jobs" value={String(overview.training.total_jobs)} />
                  <KpiCard label="Running" value={String(overview.training.running_jobs)} colour={overview.training.running_jobs > 0 ? 'text-blue-700' : 'text-pipeline-800'} />
                  <KpiCard label="Completed" value={String(overview.training.completed_jobs)} colour="text-green-700" />
                  <KpiCard
                    label="Best Val Acc"
                    value={overview.training.best_val_accuracy !== null
                      ? `${(overview.training.best_val_accuracy * 100).toFixed(2)}%`
                      : '—'}
                    colour="text-purple-700"
                  />
                </div>
              </section>
            </div>
          )}

          {/* ── System tab ────────────────────────────────────────────────── */}
          {activeTab === 'system' && (
            <div className="card">
              <h2 className="section-title mb-4">System Health</h2>
              {system ? (
                <SystemHealthPanel data={system} />
              ) : (
                <LoadingSpinner variant="card" message="Loading system metrics…" />
              )}
            </div>
          )}

          {/* ── Inference tab ─────────────────────────────────────────────── */}
          {activeTab === 'inference' && (
            <div className="card">
              <h2 className="section-title mb-4">Inference Metrics</h2>
              {inference ? (
                <InferenceMetricsPanel data={inference} />
              ) : (
                <LoadingSpinner variant="card" message="Loading inference metrics…" />
              )}
            </div>
          )}

          {/* ── Training tab ──────────────────────────────────────────────── */}
          {activeTab === 'training' && (
            <div className="card">
              <h2 className="section-title mb-4">Training Metrics</h2>
              {training ? (
                <TrainingMetricsPanel data={training} />
              ) : (
                <LoadingSpinner variant="card" message="Loading training metrics…" />
              )}
            </div>
          )}

          {/* ── History tab ───────────────────────────────────────────────── */}
          {activeTab === 'history' && (
            <div className="card space-y-5">
              <h2 className="section-title">Metrics History</h2>

              {/* Controls */}
              <div className="flex flex-wrap gap-4 items-end">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
                    Metric Type
                  </label>
                  <select
                    value={historyType}
                    onChange={(e) => setHistoryType(e.target.value as HistoryMetricType)}
                    className="rounded-lg border border-pipeline-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    aria-label="Metric type for history chart"
                  >
                    <option value="system">System</option>
                    <option value="inference">Inference</option>
                    <option value="training">Training</option>
                    <option value="overview">Overview</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-pipeline-500 uppercase tracking-wide">
                    Lookback Window
                  </label>
                  <select
                    value={historyHours}
                    onChange={(e) => setHistoryHours(Number(e.target.value))}
                    className="rounded-lg border border-pipeline-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    aria-label="History lookback window"
                  >
                    {[1, 6, 12, 24, 48, 72, 168].map((h) => (
                      <option key={h} value={h}>
                        {h < 24 ? `${h}h` : `${h / 24}d`}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={fetchHistory}
                  className="text-sm font-medium text-blue-600 border border-blue-200 rounded-lg px-4 py-2 hover:bg-blue-50 transition-colors"
                  aria-label="Load history data"
                >
                  Load
                </button>
              </div>

              {/* Chart */}
              {historyLoading ? (
                <LoadingSpinner variant="card" message="Loading history…" />
              ) : (
                <MetricsHistoryChart
                  data={historyData}
                  metrics={HISTORY_METRIC_LINES[historyType]}
                  height={280}
                  title={`${historyType.charAt(0).toUpperCase() + historyType.slice(1)} — last ${historyHours}h`}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

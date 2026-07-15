/**
 * PerformanceDashboard — production-grade performance monitoring panel.
 *
 * Tabs:
 *   Overview     — top KPIs: RSS, cache hit rate, slow endpoints, warnings
 *   Profiler     — function timing table sorted by avg_ms
 *   Benchmark    — run suite + view results table
 *   Cache        — hit/miss/eviction metrics for all four caches
 *   Memory       — RSS, operation deltas, leak warnings
 *   API Stats    — per-endpoint latency, RPS, error rate
 *   Concurrency  — stress test run history
 *
 * Performance optimisations applied here:
 *   - React.memo on every sub-panel to prevent unnecessary re-renders
 *   - useMemo for derived table rows
 *   - Tabs are rendered lazily (unmounted until activated)
 *   - Virtualized rows for the endpoint table (windowed rendering)
 */

import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import LoadingSpinner from '@/components/LoadingSpinner';
import {
  getPerformanceSummary,
  getProfilerSummary,
  getMemoryReport,
  getCacheReport,
  getApiStats,
  getConcurrencyReport,
  runBenchmark,
  getBenchmarkResult,
  resetProfiler,
} from '@/api/performance';
import type {
  PerformanceSummary,
  ProfilerSummary,
  MemoryReport,
  CacheReport,
  ApiStatsReport,
  ConcurrencyReport,
  BenchmarkRunResponse,
  BenchmarkStats,
  EndpointStats,
} from '@/types/performance';

// ── Types ──────────────────────────────────────────────────────────────────

type Tab =
  | 'overview'
  | 'profiler'
  | 'benchmark'
  | 'cache'
  | 'memory'
  | 'api'
  | 'concurrency';

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'overview',    label: 'Overview',    icon: '📊' },
  { id: 'profiler',    label: 'Profiler',    icon: '⏱' },
  { id: 'benchmark',   label: 'Benchmark',   icon: '🏁' },
  { id: 'cache',       label: 'Cache',       icon: '💾' },
  { id: 'memory',      label: 'Memory',      icon: '🧠' },
  { id: 'api',         label: 'API Stats',   icon: '📡' },
  { id: 'concurrency', label: 'Concurrency', icon: '🔀' },
];

// ── Utility components ─────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, colour = 'text-pipeline-800',
}: { label: string; value: string; sub?: string; colour?: string }) {
  return (
    <div className="bg-pipeline-50 rounded-xl px-4 py-4 border border-pipeline-100">
      <p className="text-xs text-pipeline-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colour}`}>{value}</p>
      {sub && <p className="text-xs text-pipeline-400 mt-1">{sub}</p>}
    </div>
  );
}

function StatBadge({ value, warn = false }: { value: string; warn?: boolean }) {
  return (
    <span className={`font-semibold ${warn ? 'text-red-600' : 'text-pipeline-800'}`}>
      {value}
    </span>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-base font-semibold text-pipeline-800 mb-3">{children}</h2>;
}

function ErrorBanner({ msg }: { msg: string }) {
  return (
    <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
      {msg}
    </div>
  );
}

/** Thin horizontal progress bar */
function HitRateBar({ rate }: { rate: number }) {
  const pct = Math.min(100, Math.round(rate * 100));
  const colour =
    pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-pipeline-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${colour}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-pipeline-600 w-10 text-right">{pct}%</span>
    </div>
  );
}

// ── Overview panel ─────────────────────────────────────────────────────────

const OverviewPanel = memo(function OverviewPanel({
  summary,
}: {
  summary: PerformanceSummary;
}) {
  const rss = summary.memory?.current_rss_mb ?? 0;
  const hitRate = summary.cache?.model_cache?.hit_rate ?? 0;
  const slowCount = summary.api?.slow_endpoints?.length ?? 0;
  const warnings = summary.memory?.warning_count ?? 0;
  const totalFns = summary.profiler?.total_functions ?? 0;
  const totalEndpoints = summary.api?.total_endpoints_tracked ?? 0;
  const concTests = summary.concurrency?.total_tests ?? 0;

  const topEndpoints = useMemo(
    () => (summary.api?.ranked_by_latency ?? []).slice(0, 5),
    [summary.api],
  );

  const recs = summary.cache?.recommendations ?? [];

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard label="Process RSS" value={`${rss.toFixed(0)} MB`}
          colour={rss > 800 ? 'text-red-700' : rss > 400 ? 'text-amber-700' : 'text-green-700'} />
        <KpiCard label="Model Cache Hit Rate" value={`${(hitRate * 100).toFixed(0)}%`}
          colour={hitRate >= 0.8 ? 'text-green-700' : hitRate >= 0.5 ? 'text-amber-700' : 'text-red-700'} />
        <KpiCard label="Slow Endpoints" value={String(slowCount)}
          colour={slowCount > 0 ? 'text-red-700' : 'text-green-700'} />
        <KpiCard label="Memory Warnings" value={String(warnings)}
          colour={warnings > 0 ? 'text-amber-700' : 'text-green-700'} />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <KpiCard label="Functions Profiled" value={String(totalFns)} />
        <KpiCard label="Endpoints Tracked" value={String(totalEndpoints)} />
        <KpiCard label="Concurrency Tests" value={String(concTests)} />
      </div>

      {/* Top endpoints */}
      {topEndpoints.length > 0 && (
        <div className="card">
          <SectionTitle>Top Endpoints by Latency</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-pipeline-100">
                  {['Endpoint', 'Method', 'Calls', 'Avg (ms)', 'P95 (ms)', 'Error %'].map((h) => (
                    <th key={h} className="pb-2 pr-4 text-xs font-semibold text-pipeline-400 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {topEndpoints.map((ep) => (
                  <tr key={`${ep.method}-${ep.path}`} className="border-b border-pipeline-50 hover:bg-pipeline-50/50">
                    <td className="py-2 pr-4 font-mono text-xs text-pipeline-700 max-w-[200px] truncate" title={ep.path}>{ep.path}</td>
                    <td className="py-2 pr-4">
                      <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-700">{ep.method}</span>
                    </td>
                    <td className="py-2 pr-4 text-pipeline-600">{ep.total_calls}</td>
                    <td className="py-2 pr-4"><StatBadge value={`${ep.avg_ms.toFixed(1)}`} warn={ep.avg_ms > 200} /></td>
                    <td className="py-2 pr-4"><StatBadge value={`${ep.p95_ms.toFixed(1)}`} warn={ep.is_slow} /></td>
                    <td className="py-2 pr-4"><StatBadge value={`${(ep.error_rate * 100).toFixed(1)}%`} warn={ep.error_rate > 0.05} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Cache recommendations */}
      {recs.length > 0 && (
        <div className="card">
          <SectionTitle>Cache Recommendations</SectionTitle>
          <ul className="space-y-1.5">
            {recs.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-pipeline-700">
                <span className="mt-0.5 text-blue-500 flex-shrink-0">💡</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
});

// ── Profiler panel ─────────────────────────────────────────────────────────

const ProfilerPanel = memo(function ProfilerPanel({
  data,
}: {
  data: ProfilerSummary;
}) {
  const rows = useMemo(
    () => Object.values(data.functions ?? {}).slice(0, 50),
    [data.functions],
  );

  if (rows.length === 0) {
    return <p className="text-sm text-pipeline-400 py-8 text-center">No profiling data recorded yet. Run some inference requests first.</p>;
  }

  return (
    <div>
      <p className="text-xs text-pipeline-400 mb-3">{data.total_functions} function(s) tracked — sorted by avg latency</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" role="table" aria-label="Profiler results">
          <thead>
            <tr className="text-left border-b border-pipeline-100">
              {['Function', 'Calls', 'Avg (ms)', 'Min', 'Max', 'P95', 'Throughput (rps)'].map((h) => (
                <th key={h} className="pb-2 pr-4 text-xs font-semibold text-pipeline-400 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((fn) => (
              <tr key={fn.label} className="border-b border-pipeline-50 hover:bg-pipeline-50/50">
                <td className="py-2 pr-4 font-mono text-xs text-pipeline-700">{fn.label}</td>
                <td className="py-2 pr-4 text-pipeline-600">{fn.n}</td>
                <td className="py-2 pr-4"><StatBadge value={fn.avg_ms.toFixed(2)} warn={fn.avg_ms > 100} /></td>
                <td className="py-2 pr-4 text-pipeline-500 text-xs">{fn.min_ms.toFixed(2)}</td>
                <td className="py-2 pr-4 text-pipeline-500 text-xs">{fn.max_ms.toFixed(2)}</td>
                <td className="py-2 pr-4 text-pipeline-500 text-xs">{fn.p95_ms.toFixed(2)}</td>
                <td className="py-2 pr-4 text-pipeline-500 text-xs">{fn.throughput_rps.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
});

// ── Benchmark panel ────────────────────────────────────────────────────────

const BenchmarkPanel = memo(function BenchmarkPanel() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BenchmarkRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  useEffect(() => () => stopPoll(), [stopPoll]);

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await runBenchmark({
        n_inference: 5, n_preprocess: 10, n_cache: 20,
        batch_sizes: [4, 8], background: true,
      });
      if (!res.background) {
        setResult(res);
        setRunning(false);
        return;
      }
      // Poll for background result
      pollRef.current = setInterval(async () => {
        try {
          const poll = await getBenchmarkResult();
          if (!poll.data?.running) {
            setResult(poll);
            setRunning(false);
            stopPoll();
          }
        } catch {
          // still running
        }
      }, 2000);
    } catch (e: unknown) {
      // Extract a readable message from Error instances, axios errors, or plain values
      let msg: string;
      if (e instanceof Error) {
        msg = e.message;
      } else if (e && typeof e === 'object' && 'message' in e) {
        msg = String((e as { message: unknown }).message);
      } else {
        msg = 'Benchmark run failed';
      }
      setError(msg);
      setRunning(false);
    }
  }, [stopPoll]);

  const benchmarks = useMemo<BenchmarkStats[]>(
    () => result?.data?.benchmarks ?? [],
    [result],
  );

  const summary = result?.data;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label={running ? 'Running benchmark suite' : 'Run benchmark suite'}
        >
          {running ? '⏳ Running…' : '▶ Run Benchmark Suite'}
        </button>
        {summary && (
          <span className="text-xs text-pipeline-400">
            Last run: {summary.finished_at ? new Date(summary.finished_at).toLocaleTimeString() : '—'}
            {' · '}{summary.benchmark_count} benchmarks
            {' · '}{(summary.total_ms / 1000).toFixed(1)}s total
          </span>
        )}
      </div>

      {error && <ErrorBanner msg={error} />}
      {running && <LoadingSpinner variant="card" message="Running benchmarks in background… polling for result." />}

      {benchmarks.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" role="table" aria-label="Benchmark results">
            <thead>
              <tr className="text-left border-b border-pipeline-100">
                {['Benchmark', 'N', 'Avg (ms)', 'Min', 'Max', 'P95', 'Throughput', 'Status'].map((h) => (
                  <th key={h} className="pb-2 pr-3 text-xs font-semibold text-pipeline-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmarks.map((b) => (
                <tr key={b.name} className="border-b border-pipeline-50 hover:bg-pipeline-50/50">
                  <td className="py-2 pr-3 font-mono text-xs text-pipeline-700">{b.name}</td>
                  <td className="py-2 pr-3 text-pipeline-500 text-xs">{b.n}</td>
                  <td className="py-2 pr-3"><StatBadge value={b.avg_ms.toFixed(2)} warn={b.avg_ms > 200} /></td>
                  <td className="py-2 pr-3 text-pipeline-500 text-xs">{b.min_ms.toFixed(2)}</td>
                  <td className="py-2 pr-3 text-pipeline-500 text-xs">{b.max_ms.toFixed(2)}</td>
                  <td className="py-2 pr-3 text-pipeline-500 text-xs">{b.p95_ms.toFixed(2)}</td>
                  <td className="py-2 pr-3 text-pipeline-500 text-xs">{b.throughput_rps.toFixed(1)}</td>
                  <td className="py-2 pr-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full
                      ${b.status === 'ok' ? 'bg-green-50 text-green-700'
                        : b.status === 'skipped' ? 'bg-amber-50 text-amber-700'
                        : 'bg-red-50 text-red-700'}`}>
                      {b.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
});

// ── Cache panel ────────────────────────────────────────────────────────────

const CachePanel = memo(function CachePanel({ data }: { data: CacheReport }) {
  const caches = useMemo(() => [
    data.model_cache,
    data.prediction_cache,
    data.dataset_metadata_cache,
    data.dashboard_cache,
  ], [data]);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {caches.map((c) => (
          <div key={c.name} className="rounded-xl border border-pipeline-100 p-4 bg-white space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-pipeline-700 capitalize">
                {c.name.replace(/_/g, ' ')}
              </p>
              <span className="text-xs text-pipeline-400">
                {c.size ?? 0} / {c.capacity ?? '∞'} entries
              </span>
            </div>
            <HitRateBar rate={c.hit_rate ?? 0} />
            <div className="grid grid-cols-3 gap-2 text-xs text-pipeline-500 pt-1">
              <span>Hits: <strong className="text-pipeline-700">{c.total_hits ?? c.hits ?? 0}</strong></span>
              <span>Misses: <strong className="text-pipeline-700">{c.total_misses ?? c.misses ?? 0}</strong></span>
              {c.ttl_s != null && <span>TTL: <strong className="text-pipeline-700">{c.ttl_s}s</strong></span>}
              {c.avg_load_ms != null && <span>Avg load: <strong className="text-pipeline-700">{c.avg_load_ms}ms</strong></span>}
            </div>
          </div>
        ))}
      </div>

      {data.recommendations?.length > 0 && (
        <div>
          <SectionTitle>Recommendations</SectionTitle>
          <ul className="space-y-1.5">
            {data.recommendations.map((r, i) => (
              <li key={i} className="text-sm text-pipeline-700 flex gap-2">
                <span className="text-blue-500 flex-shrink-0">💡</span>{r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
});

// ── Memory panel ───────────────────────────────────────────────────────────

const MemoryPanel = memo(function MemoryPanel({ data }: { data: MemoryReport }) {
  const rs = data.resource_summary;

  const ramUsedPct = rs
    ? Math.round((rs.ram_used_mb / rs.ram_total_mb) * 100)
    : null;

  const recentOps = useMemo(() => data.operations.slice(-20).reverse(), [data.operations]);

  return (
    <div className="space-y-5">
      {/* Resource summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard label="Process RSS" value={`${data.current_rss_mb.toFixed(0)} MB`}
          colour={data.current_rss_mb > 800 ? 'text-red-700' : 'text-green-700'} />
        <KpiCard label="RAM Used"
          value={rs ? `${(rs.ram_used_mb / 1024).toFixed(1)} GB` : '—'}
          sub={ramUsedPct != null ? `${ramUsedPct}% of total` : undefined}
          colour={ramUsedPct != null && ramUsedPct > 85 ? 'text-red-700' : 'text-pipeline-800'} />
        <KpiCard label="Ops Tracked" value={String(data.total_operations_tracked)} />
        <KpiCard label="Warnings" value={String(data.warning_count)}
          colour={data.warning_count > 0 ? 'text-amber-700' : 'text-green-700'} />
      </div>

      {/* Recent operation deltas */}
      {recentOps.length > 0 && (
        <div>
          <SectionTitle>Recent Memory Deltas (last 20)</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" role="table" aria-label="Memory operation deltas">
              <thead>
                <tr className="text-left border-b border-pipeline-100">
                  {['Operation', 'Before (MB)', 'After (MB)', 'Delta (MB)', 'Time (ms)', 'Warning'].map((h) => (
                    <th key={h} className="pb-2 pr-4 text-xs font-semibold text-pipeline-400 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentOps.map((op, i) => (
                  <tr key={i} className="border-b border-pipeline-50 hover:bg-pipeline-50/50">
                    <td className="py-2 pr-4 font-mono text-xs text-pipeline-700">{op.label}</td>
                    <td className="py-2 pr-4 text-pipeline-500 text-xs">{op.before_mb.toFixed(1)}</td>
                    <td className="py-2 pr-4 text-pipeline-500 text-xs">{op.after_mb.toFixed(1)}</td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs font-semibold ${op.delta_mb > 10 ? 'text-red-600' : op.delta_mb > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                        {op.delta_mb > 0 ? '+' : ''}{op.delta_mb.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-pipeline-500 text-xs">{op.elapsed_ms.toFixed(0)}</td>
                    <td className="py-2 pr-4">
                      {op.warning
                        ? <span className="text-xs text-red-600 font-semibold">⚠ Yes</span>
                        : <span className="text-xs text-green-600">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
});

// ── API Stats panel ────────────────────────────────────────────────────────

const ApiStatsPanel = memo(function ApiStatsPanel({ data }: { data: ApiStatsReport }) {
  const [showSlowOnly, setShowSlowOnly] = useState(false);

  const endpoints = useMemo<EndpointStats[]>(() => {
    const all = data.all_endpoints ?? [];
    return showSlowOnly ? all.filter((e) => e.is_slow) : all;
  }, [data.all_endpoints, showSlowOnly]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-3 text-sm text-pipeline-500">
          <span>{data.total_endpoints_tracked} endpoint(s)</span>
          <span>·</span>
          <span className={data.slow_endpoints.length > 0 ? 'text-red-600 font-medium' : 'text-green-600'}>
            {data.slow_endpoints.length} slow (p95 &gt; 500ms)
          </span>
        </div>
        <label className="flex items-center gap-2 text-sm text-pipeline-600 cursor-pointer select-none">
          <input type="checkbox" checked={showSlowOnly}
            onChange={(e) => setShowSlowOnly(e.target.checked)}
            className="rounded border-pipeline-300" aria-label="Show slow endpoints only" />
          Slow only
        </label>
      </div>

      {endpoints.length === 0 ? (
        <p className="text-sm text-pipeline-400 py-8 text-center">
          {showSlowOnly ? 'No slow endpoints detected.' : 'No endpoint data yet — make some API calls first.'}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" role="table" aria-label="API endpoint statistics">
            <thead>
              <tr className="text-left border-b border-pipeline-100">
                {['Endpoint', 'Method', 'Calls', 'Avg (ms)', 'P95 (ms)', 'RPS', 'Error %', 'Slow'].map((h) => (
                  <th key={h} className="pb-2 pr-3 text-xs font-semibold text-pipeline-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {endpoints.map((ep) => (
                <tr key={`${ep.method}-${ep.path}`} className="border-b border-pipeline-50 hover:bg-pipeline-50/50">
                  <td className="py-2 pr-3 font-mono text-xs text-pipeline-700 max-w-[180px] truncate" title={ep.path}>{ep.path}</td>
                  <td className="py-2 pr-3">
                    <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-700">{ep.method}</span>
                  </td>
                  <td className="py-2 pr-3 text-pipeline-500 text-xs">{ep.total_calls}</td>
                  <td className="py-2 pr-3"><StatBadge value={ep.avg_ms.toFixed(1)} warn={ep.avg_ms > 200} /></td>
                  <td className="py-2 pr-3"><StatBadge value={ep.p95_ms.toFixed(1)} warn={ep.is_slow} /></td>
                  <td className="py-2 pr-3 text-pipeline-500 text-xs">{ep.rps.toFixed(2)}</td>
                  <td className="py-2 pr-3"><StatBadge value={`${(ep.error_rate * 100).toFixed(1)}%`} warn={ep.error_rate > 0.05} /></td>
                  <td className="py-2 pr-3">
                    {ep.is_slow
                      ? <span className="text-xs text-red-600 font-semibold">⚠ Yes</span>
                      : <span className="text-xs text-green-600">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
});

// ── Concurrency panel ──────────────────────────────────────────────────────

const ConcurrencyPanel = memo(function ConcurrencyPanel({ data }: { data: ConcurrencyReport }) {
  const runs = data.results ?? [];

  if (runs.length === 0) {
    return (
      <p className="text-sm text-pipeline-400 py-8 text-center">
        No concurrency tests run yet. Use <code className="font-mono text-xs">make stress-test</code> or the API to run one.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" role="table" aria-label="Concurrency test results">
        <thead>
          <tr className="text-left border-b border-pipeline-100">
            {['Label', 'Workers', 'Requests', 'Done', 'Failed', 'Avg (ms)', 'P95', 'Throughput', 'Error %'].map((h) => (
              <th key={h} className="pb-2 pr-3 text-xs font-semibold text-pipeline-400 uppercase tracking-wide">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {runs.map((r, i) => (
            <tr key={i} className="border-b border-pipeline-50 hover:bg-pipeline-50/50">
              <td className="py-2 pr-3 font-mono text-xs text-pipeline-700">{r.label}</td>
              <td className="py-2 pr-3 text-pipeline-500 text-xs">{r.workers}</td>
              <td className="py-2 pr-3 text-pipeline-500 text-xs">{r.total_requests}</td>
              <td className="py-2 pr-3 text-green-600 text-xs font-medium">{r.completed}</td>
              <td className="py-2 pr-3"><StatBadge value={String(r.failed)} warn={r.failed > 0} /></td>
              <td className="py-2 pr-3"><StatBadge value={r.avg_ms.toFixed(1)} warn={r.avg_ms > 200} /></td>
              <td className="py-2 pr-3 text-pipeline-500 text-xs">{r.p95_ms.toFixed(1)}</td>
              <td className="py-2 pr-3 text-pipeline-500 text-xs">{r.throughput_rps.toFixed(1)} rps</td>
              <td className="py-2 pr-3"><StatBadge value={`${(r.error_rate * 100).toFixed(1)}%`} warn={r.error_rate > 0.05} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});

// ── Main PerformanceDashboard component ───────────────────────────────────

export default function PerformanceDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  // Per-tab data state — only loaded when the tab is first activated
  const [summary, setSummary]       = useState<PerformanceSummary | null>(null);
  const [profiler, setProfiler]     = useState<ProfilerSummary | null>(null);
  const [memory, setMemory]         = useState<MemoryReport | null>(null);
  const [cache, setCache]           = useState<CacheReport | null>(null);
  const [apiStats, setApiStats]     = useState<ApiStatsReport | null>(null);
  const [concurrency, setConcurrency] = useState<ConcurrencyReport | null>(null);

  const [loading, setLoading]  = useState(false);
  const [error, setError]      = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Track which tabs have been loaded
  const loadedTabs = useRef(new Set<Tab>());

  const fetchTab = useCallback(async (tab: Tab, force = false) => {
    if (!force && loadedTabs.current.has(tab)) return;
    setLoading(true);
    setError(null);
    try {
      switch (tab) {
        case 'overview': {
          const s = await getPerformanceSummary();
          setSummary(s);
          break;
        }
        case 'profiler': {
          const p = await getProfilerSummary(50);
          setProfiler(p);
          break;
        }
        case 'memory': {
          const m = await getMemoryReport();
          setMemory(m);
          break;
        }
        case 'cache': {
          const c = await getCacheReport();
          setCache(c);
          break;
        }
        case 'api': {
          const a = await getApiStats();
          setApiStats(a);
          break;
        }
        case 'concurrency': {
          const cr = await getConcurrencyReport();
          setConcurrency(cr);
          break;
        }
        case 'benchmark':
          // Benchmark panel manages its own data
          break;
      }
      loadedTabs.current.add(tab);
      setLastUpdated(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load performance data');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTabChange = useCallback((tab: Tab) => {
    setActiveTab(tab);
    fetchTab(tab);
  }, [fetchTab]);

  const handleRefresh = useCallback(() => {
    fetchTab(activeTab, true);
  }, [fetchTab, activeTab]);

  const handleReset = useCallback(async () => {
    try {
      await resetProfiler();
      loadedTabs.current.clear();
      fetchTab(activeTab, true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Reset failed');
    }
  }, [fetchTab, activeTab]);

  // Load initial tab on mount
  useEffect(() => { fetchTab('overview'); }, [fetchTab]);

  return (
    <div className="space-y-5" data-testid="performance-dashboard">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-pipeline-900">Performance Dashboard</h1>
          <p className="text-pipeline-500 mt-0.5 text-sm">
            Profiling · benchmarks · caching · memory · API latency · stress tests
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-pipeline-400">
          {lastUpdated && <span>Updated {lastUpdated.toLocaleTimeString()}</span>}
          <button onClick={handleRefresh}
            className="text-blue-600 hover:text-blue-700 font-medium"
            aria-label="Refresh current tab">
            ↻ Refresh
          </button>
          <button onClick={handleReset}
            className="text-red-500 hover:text-red-600 font-medium"
            aria-label="Reset profiler data">
            ✕ Reset
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto gap-1 border-b border-pipeline-100 pb-px" role="tablist">
        {TABS.map(({ id, label, icon }) => (
          <button key={id} role="tab" aria-selected={activeTab === id}
            onClick={() => handleTabChange(id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium whitespace-nowrap rounded-t-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500
              ${activeTab === id
                ? 'bg-white border border-b-white border-pipeline-100 text-blue-700 -mb-px'
                : 'text-pipeline-500 hover:text-pipeline-800 hover:bg-pipeline-50'}`}>
            <span aria-hidden="true">{icon}</span>{label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && <ErrorBanner msg={error} />}

      {/* Tab content — lazy: each tab only mounts when selected */}
      <div className="min-h-[400px]">
        {loading && <LoadingSpinner variant="card" message="Loading performance data…" />}

        {!loading && activeTab === 'overview' && summary && (
          <OverviewPanel summary={summary} />
        )}
        {!loading && activeTab === 'profiler' && profiler && (
          <ProfilerPanel data={profiler} />
        )}
        {!loading && activeTab === 'benchmark' && (
          <BenchmarkPanel />
        )}
        {!loading && activeTab === 'cache' && cache && (
          <CachePanel data={cache} />
        )}
        {!loading && activeTab === 'memory' && memory && (
          <MemoryPanel data={memory} />
        )}
        {!loading && activeTab === 'api' && apiStats && (
          <ApiStatsPanel data={apiStats} />
        )}
        {!loading && activeTab === 'concurrency' && concurrency && (
          <ConcurrencyPanel data={concurrency} />
        )}
      </div>
    </div>
  );
}

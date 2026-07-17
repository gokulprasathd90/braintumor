/**
 * src/types/performance.ts — TypeScript models for the performance module.
 *
 * Mirrors the FastAPI response schemas from app/api/performance_routes.py
 * and the data classes in app/performance/*.py
 */

// ── Profiler ───────────────────────────────────────────────────────────────

export interface FunctionStats {
  label: string;
  n: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
  median_ms: number;
  p95_ms: number;
  p99_ms: number;
  throughput_rps: number;
  timestamp: string;
}

export interface ProfilerSummary {
  total_functions: number;
  functions: Record<string, FunctionStats>;
}

// ── Memory ─────────────────────────────────────────────────────────────────

export interface MemoryDelta {
  label: string;
  before_mb: number;
  after_mb: number;
  delta_mb: number;
  elapsed_ms: number;
  warning: boolean;
  timestamp: string;
}

export interface MemorySnapshot {
  label: string;
  rss_mb: number;
  tracemalloc_kb: number | null;
  timestamp: string;
}

export interface ResourceSummary {
  ram_total_mb: number;
  ram_used_mb: number;
  ram_available_mb: number;
  ram_percent: number;
  process_rss_mb: number;
}

export interface MemoryReport {
  timestamp: string;
  current_rss_mb: number;
  total_operations_tracked: number;
  warning_count: number;
  warnings: MemoryDelta[];
  operations: MemoryDelta[];
  snapshots: MemorySnapshot[];
  resource_summary: ResourceSummary;
}

// ── Cache ──────────────────────────────────────────────────────────────────

export interface CacheMetrics {
  name: string;
  capacity?: number;
  size: number;
  utilization?: number;
  hit_rate: number;
  total_hits?: number;
  total_misses?: number;
  total_evictions?: number;
  avg_load_ms?: number | null;
  hits?: number;
  misses?: number;
  ttl_s?: number;
  timestamp?: string;
}

export interface CacheReport {
  timestamp: string;
  model_cache: CacheMetrics;
  prediction_cache: CacheMetrics;
  dataset_metadata_cache: CacheMetrics;
  dashboard_cache: CacheMetrics;
  recommendations: string[];
}

// ── API Stats ──────────────────────────────────────────────────────────────

export interface EndpointStats {
  path: string;
  method: string;
  total_calls: number;
  errors: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
  median_ms: number;
  p95_ms: number;
  p99_ms: number;
  error_rate: number;
  rps: number;
  is_slow: boolean;
  timestamp: string;
}

export interface ApiStatsReport {
  timestamp: string;
  total_endpoints_tracked: number;
  slow_endpoints: EndpointStats[];
  ranked_by_latency: EndpointStats[];
  all_endpoints: EndpointStats[];
}

// ── Concurrency ────────────────────────────────────────────────────────────

export interface ConcurrencyRun {
  label: string;
  workers: number;
  total_requests: number;
  completed: number;
  failed: number;
  error_rate: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
  median_ms: number;
  p95_ms: number;
  p99_ms: number;
  throughput_rps: number;
  total_elapsed_ms: number;
  sample_errors: string[];
  timestamp: string;
}

export interface ConcurrencyReport {
  timestamp: string;
  total_tests: number;
  results: ConcurrencyRun[];
}

// ── Benchmark ─────────────────────────────────────────────────────────────

export interface BenchmarkStats {
  name: string;
  n: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
  median_ms: number;
  p95_ms: number;
  throughput_rps: number;
  total_ms: number;
  status: 'ok' | 'skipped' | 'error';
  error: string | null;
  timestamp: string;
  [key: string]: unknown;
}

export interface BenchmarkResult {
  suite_name: string;
  started_at: string;
  finished_at: string | null;
  total_ms: number;
  benchmark_count: number;
  benchmarks: BenchmarkStats[];
}

export interface BenchmarkRunRequest {
  n_inference?: number;
  n_preprocess?: number;
  n_cache?: number;
  batch_sizes?: number[];
  background?: boolean;
}

export interface BenchmarkRunResponse {
  success: boolean;
  message: string;
  data: BenchmarkResult & { running?: boolean } | null;
  background: boolean;
}

export interface SingleBenchmarkRequest {
  name: string;
  n?: number;
}

// ── Performance Summary ────────────────────────────────────────────────────

export interface PerformanceSummary {
  report_type: string;
  generated_at: string;
  system: Record<string, unknown>;
  inference: Record<string, unknown>;
  cache: CacheReport;
  memory: MemoryReport;
  api: ApiStatsReport;
  profiler: ProfilerSummary;
  concurrency: ConcurrencyReport;
}

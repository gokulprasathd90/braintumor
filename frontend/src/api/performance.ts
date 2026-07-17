/**
 * src/api/performance.ts — Performance monitoring API endpoints.
 *
 * Maps to:
 *   GET  /api/v1/performance/summary
 *   GET  /api/v1/performance/report/html
 *   GET  /api/v1/performance/profiler
 *   GET  /api/v1/performance/memory
 *   GET  /api/v1/performance/cache
 *   GET  /api/v1/performance/api-stats
 *   GET  /api/v1/performance/concurrency
 *   POST /api/v1/performance/benchmark/run
 *   GET  /api/v1/performance/benchmark/result
 *   POST /api/v1/performance/benchmark/single
 *   DELETE /api/v1/performance/profiler/reset
 */

import { get, post } from './client';
import { apiClient } from './client';
import type {
  PerformanceSummary,
  ProfilerSummary,
  MemoryReport,
  CacheReport,
  ApiStatsReport,
  ConcurrencyReport,
  BenchmarkStats,
  BenchmarkResult,
  BenchmarkRunRequest,
  BenchmarkRunResponse,
  SingleBenchmarkRequest,
} from '@/types/performance';

interface PerformanceResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

// ── Summary ────────────────────────────────────────────────────────────────

export async function getPerformanceSummary(): Promise<PerformanceSummary> {
  const res = await get<PerformanceResponse<PerformanceSummary>>('/performance/summary');
  return res.data;
}

// ── Profiler ───────────────────────────────────────────────────────────────

export async function getProfilerSummary(top = 20): Promise<ProfilerSummary> {
  const res = await get<PerformanceResponse<ProfilerSummary>>(
    `/performance/profiler?top=${top}`,
  );
  return res.data;
}

// ── Memory ─────────────────────────────────────────────────────────────────

export async function getMemoryReport(): Promise<MemoryReport> {
  const res = await get<PerformanceResponse<MemoryReport>>('/performance/memory');
  return res.data;
}

// ── Cache ──────────────────────────────────────────────────────────────────

export async function getCacheReport(): Promise<CacheReport> {
  const res = await get<PerformanceResponse<CacheReport>>('/performance/cache');
  return res.data;
}

// ── API Stats ──────────────────────────────────────────────────────────────

export async function getApiStats(slowOnly = false): Promise<ApiStatsReport> {
  const query = slowOnly ? '?slow_only=true' : '';
  const res = await get<PerformanceResponse<ApiStatsReport>>(
    `/performance/api-stats${query}`,
  );
  return res.data;
}

// ── Concurrency ────────────────────────────────────────────────────────────

export async function getConcurrencyReport(): Promise<ConcurrencyReport> {
  const res = await get<PerformanceResponse<ConcurrencyReport>>(
    '/performance/concurrency',
  );
  return res.data;
}

// ── Benchmark ─────────────────────────────────────────────────────────────

export async function runBenchmark(
  body: BenchmarkRunRequest,
): Promise<BenchmarkRunResponse> {
  return post<BenchmarkRunResponse>('/performance/benchmark/run', body);
}

export async function getBenchmarkResult(): Promise<BenchmarkRunResponse> {
  return get<BenchmarkRunResponse>('/performance/benchmark/result');
}

export async function runSingleBenchmark(
  body: SingleBenchmarkRequest,
): Promise<PerformanceResponse<BenchmarkStats>> {
  return post<PerformanceResponse<BenchmarkStats>>(
    '/performance/benchmark/single',
    body,
  );
}

// ── Reset ──────────────────────────────────────────────────────────────────

export async function resetProfiler(): Promise<{ cleared: string[]; errors: string[] }> {
  const res = await apiClient.delete<PerformanceResponse<{ cleared: string[]; errors: string[] }>>(
    '/performance/profiler/reset',
  );
  return res.data.data;
}

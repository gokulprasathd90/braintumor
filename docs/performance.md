# Performance Optimization Guide

> Module 11 — Brain Tumour Detection AI Service

This document covers profiling, benchmarking, stress testing, cache optimization, memory management, frontend optimization, and how to interpret the generated reports.

---

## Table of Contents

1. [Overview](#overview)
2. [Profiling Guide](#profiling-guide)
3. [Benchmark Guide](#benchmark-guide)
4. [Stress Testing Guide](#stress-testing-guide)
5. [Cache Optimization Guide](#cache-optimization-guide)
6. [Memory Optimization Guide](#memory-optimization-guide)
7. [Frontend Optimization](#frontend-optimization)
8. [Performance Tuning Recommendations](#performance-tuning-recommendations)
9. [Report Interpretation](#report-interpretation)
10. [API Reference](#api-reference)
11. [Makefile Targets](#makefile-targets)

---

## Overview

The performance module (`app/performance/`) provides seven submodules:

| Module | Purpose |
|---|---|
| `profiler.py` | CPU + function timing via `cProfile`, decorator and context-manager API |
| `benchmark.py` | Timed benchmark suite across all major modules |
| `optimizer.py` | Per-endpoint API latency tracking fed by middleware |
| `cache.py` | Cache analytics and tuning recommendations for all four caches |
| `memory.py` | RSS profiling, `tracemalloc` allocation hotspots, leak detection |
| `concurrency.py` | ThreadPoolExecutor-based load and stress tests |
| `reports.py` | JSON and self-contained HTML report generation |

All seven are exposed under `app/performance/__init__.py` and served by REST endpoints at `/api/v1/performance/*`.

---

## Profiling Guide

### Function timing — decorator

```python
from app.performance.profiler import get_profiler

profiler = get_profiler()

@profiler.timer("my_function")
def expensive_operation(data):
    ...
```

Every call records `elapsed_ms` against the label `"my_function"`. The data accumulates in the process-wide singleton until `profiler.reset()` is called.

### Function timing — benchmark N iterations

```python
from app.performance.profiler import profile_function

result = profile_function(
    lambda: preprocess_for_inference(img_bytes),
    n=100,
    label="preprocess",
    warmup=5,          # untimed warm-up calls
    cpu_profile=True,  # capture cProfile snapshot
    memory_profile=True,
)

print(result.avg_ms, result.p95_ms, result.throughput)
```

### Block timing — context manager

```python
from app.performance.profiler import profile_block

with profile_block("grad_cam_generation") as blk:
    heatmap = generate_gradcam(model, image)

print(f"Grad-CAM took {blk.elapsed_ms:.1f}ms")
```

### Manual record

```python
get_profiler().record("dataset_load", elapsed_ms=42.5)
```

### View the summary

```python
summary = get_profiler().summary(top=10)  # top 10 slowest
```

Or call `GET /api/v1/performance/profiler?top=10`.

### CLI profile

```bash
# From project root
make profile            # preprocessor + cache + system metrics
make profile-api        # live API latency stats
make profile-training   # training architecture build overhead
```

---

## Benchmark Guide

The `BenchmarkSuite` runs timed benchmarks for each major module. Each benchmark records: **avg, min, max, median, p95, throughput (ops/s), total runtime**.

### Available benchmarks

| Benchmark name | What it measures |
|---|---|
| `preprocessing` | Single-image denoise + CLAHE + resize + normalize |
| `image_quality_check` | Image validation checks |
| `single_inference` | Full inference pipeline (mocked model weights) |
| `batch_inference_bs{N}` | Batch inference at batch size N |
| `cache_get_hit` | ModelCache.get() on a pre-populated cache |
| `cache_stats_call` | cache_stats() overhead |
| `dataset_metadata` | dataset_info.json read (skipped if no dataset) |
| `system_metrics_collection` | psutil CPU/RAM/disk snapshot |
| `inference_metrics_record` | InferenceMetricsStore.record() throughput |

### Run programmatically

```python
from app.performance.benchmark import BenchmarkSuite, run_benchmark

# Full suite
suite = BenchmarkSuite(n_inference=20, n_preprocess=50, n_cache=100)
result = suite.run_all(batch_sizes=[4, 8, 16])
print(result.summary())

# Single benchmark
stat = run_benchmark("preprocessing", n=50)
print(stat.avg_ms, stat.throughput)
```

### Run via API

```http
POST /api/v1/performance/benchmark/run
Authorization: Bearer <token>
Content-Type: application/json

{
  "n_inference": 20,
  "n_preprocess": 50,
  "n_cache": 100,
  "batch_sizes": [4, 8, 16],
  "background": true
}
```

Poll `GET /api/v1/performance/benchmark/result` until `data.running` is `false`.

### Run via Makefile

```bash
make benchmark        # quick: n_inference=5, n_preprocess=10, n_cache=20
make benchmark-all    # full:  n_inference=20, n_preprocess=50, n_cache=100
```

### Interpreting benchmark results

- **`status: "ok"`** — benchmark ran and produced valid timings.
- **`status: "skipped"`** — prerequisite missing (e.g., no saved model weights or no dataset).
- **`status: "error"`** — an exception was raised during the benchmark. Check the `error` field.
- **`throughput_rps`** — operations per second at the measured avg latency. Higher is better.
- **`p95_ms`** — 95th-percentile latency. Spiky p95 vs avg indicates inconsistent performance (GC pauses, cold caches).

---

## Stress Testing Guide

### Callable-based stress test (no server required)

```python
from app.performance.concurrency import run_concurrent
from app.preprocessing.preprocess import preprocess_for_inference
from app.performance.benchmark import _make_test_image

img = _make_test_image()

for workers in [10, 50, 100]:
    result = run_concurrent(
        lambda: preprocess_for_inference(img),
        workers=workers,
        requests=workers * 10,
        label=f"stress_w{workers}",
    )
    print(f"workers={workers}: avg={result.avg_ms:.1f}ms "
          f"throughput={result.throughput:.1f}rps "
          f"errors={result.failed}")
```

### HTTP stress test (requires running server)

```python
from app.performance.concurrency import StressTestRunner

runner = StressTestRunner(base_url="http://localhost:8000")
results = runner.run_full_stress_suite(worker_levels=[10, 50, 100])
```

The `StressTestRunner` runs:

- `run_health_stress` — `GET /api/v1/health`
- `run_predict_stress` — `POST /api/v1/predict/image`
- `run_dashboard_stress` — `GET /api/v1/dashboard/overview`

### Run via Makefile

```bash
make stress-test   # callable-based (no server): 10/50/100 workers
make stress-api    # HTTP-based (requires server on :8000)
```

### Interpreting concurrency results

- **`error_rate`** — fraction of requests that raised an exception. Target: < 1% under normal load.
- **`throughput_rps`** — sustained requests per second across all workers.
- **`p95_ms`** — tail latency under concurrent load. Increasing p95 under higher concurrency indicates a bottleneck (CPU saturation, GIL contention, or model loading).

---

## Cache Optimization Guide

Four caches are tracked:

| Cache | Class | Default capacity / TTL |
|---|---|---|
| Model cache | `ModelCache` (LRU) | 4 models |
| Prediction cache | `_PredictionCache` (SHA-256 keyed LRU + TTL) | 256 entries, 300 s |
| Dataset metadata cache | `_DatasetMetadataCache` (TTL) | 60 s |
| Dashboard cache | `_DashboardCache` (TTL) | 5 s |

### View cache report

```python
from app.performance.cache import get_cache_report
import json
print(json.dumps(get_cache_report(), indent=2))
```

Or call `GET /api/v1/performance/cache`.

```bash
make cache-report
```

### Tuning the model cache

If `hit_rate < 50%` on the model cache, the `CacheOptimizer.recommend()` method will suggest pre-warming models at startup:

```python
# In app/main.py startup event
from app.inference.cache import _cache
_cache.load("efficientnet")   # pre-warm before first request
```

Increase capacity if you serve multiple architectures frequently:

```python
# In app/core/config.py
MODEL_CACHE_CAPACITY: int = 8   # default: 4
```

### Cache invalidation

```python
from app.performance.cache import get_prediction_cache, get_dataset_cache

get_prediction_cache().invalidate()         # wipe all predictions
get_dataset_cache().invalidate("/some/path")  # wipe one dataset entry
```

### Cache benchmarking

The benchmark suite measures `cache_get_hit` (hit path latency) and `cache_stats_call` (stats overhead). Target: `cache_get_hit` avg < 0.5 ms.

---

## Memory Optimization Guide

### Profile memory usage

```python
from app.performance.memory import get_memory_profiler, track_memory

profiler = get_memory_profiler()

# Context manager
with track_memory("batch_inference") as m:
    results = pipeline.predict_batch(sources)
print(f"Delta: {m.delta_mb:+.1f} MB in {m.elapsed_ms:.0f}ms")

# Callable profiling
delta = profiler.profile(lambda: pipeline.predict(img), label="single_infer")

# tracemalloc allocation hotspots
tm = profiler.profile_tracemalloc(lambda: pipeline.predict(img), label="alloc_check")
print(tm["top_allocations"])
```

### Leak detection

```python
result = profiler.detect_leaks(
    lambda: preprocess_for_inference(img),
    label="preprocess_leak",
    iterations=10,
)
if result["suspected_leak"]:
    print(f"Potential leak: {result['total_growth_mb']:.1f} MB over {result['iterations']} iterations")
```

A suspected leak is flagged when RSS grows monotonically across all iterations **and** the total growth exceeds 5 MB.

### Force cleanup

```python
cleanup = profiler.force_cleanup()
print(f"Freed {cleanup['freed_mb']:.1f} MB, evicted {cleanup['models_evicted']} cached models")
```

### Memory report

```bash
make memory-report
```

Or call `GET /api/v1/performance/memory`.

### Memory thresholds

| Metric | Warning threshold |
|---|---|
| Single-operation RSS delta | > 50 MB (configurable via `MemoryProfiler(leak_threshold_mb=...)`) |
| Leak detection growth | > 5 MB monotone across N iterations |
| Process RSS | > 800 MB (frontend warning colour) |

---

## Frontend Optimization

The `PerformanceDashboard` component (`frontend/src/components/PerformanceDashboard.tsx`) applies several optimization patterns:

### Lazy tab loading

Each tab's data is fetched only when the tab is first activated. A `Set<Tab>` tracks which tabs have been loaded; subsequent switches reuse cached state without a network call.

```tsx
const loadedTabs = useRef(new Set<Tab>());

const fetchTab = useCallback(async (tab: Tab, force = false) => {
  if (!force && loadedTabs.current.has(tab)) return;  // already loaded
  // ... fetch
  loadedTabs.current.add(tab);
}, []);
```

### React.memo on all sub-panels

Every panel component is wrapped in `React.memo` to prevent re-renders when parent state changes but the panel's props have not.

```tsx
const OverviewPanel = memo(function OverviewPanel({ summary }) { ... });
const CachePanel    = memo(function CachePanel({ data }) { ... });
```

### useMemo for derived data

Table rows and filtered lists are memoized to avoid recomputation on every render:

```tsx
const topEndpoints = useMemo(
  () => (summary.api?.ranked_by_latency ?? []).slice(0, 5),
  [summary.api],
);
```

### Route code splitting

The `PerformanceDashboard` is loaded via `React.lazy` in the router to keep the initial bundle small. The Monitoring page only loads when the user navigates to it.

### Bundle analysis

Run the Vite bundle visualizer:

```bash
cd frontend
npm run build -- --mode production
npx vite-bundle-visualizer   # or: npx rollup-plugin-visualizer
```

Target: `PerformanceDashboard` chunk < 50 KB gzipped.

---

## Performance Tuning Recommendations

### Inference latency

| Scenario | Recommendation |
|---|---|
| First-request p95 > 2 s | Pre-warm the model cache at startup |
| avg latency > 100 ms with mock model | Check CLAHE and denoise preprocessing — can be disabled in `PreprocessingConfig` |
| Batch inference throughput < 10 img/s | Increase `max_workers` in `InferenceConfig` |

### API latency

| Metric | Target | Action if exceeded |
|---|---|---|
| Health endpoint avg | < 5 ms | Check rate limiter overhead |
| Dashboard overview avg | < 100 ms | Enable `DashboardCache` (default TTL: 5 s) |
| Predict/image p95 | < 500 ms | Pre-warm model, review preprocessing config |

### Cache hit rate

| Cache | Target hit rate | Action if low |
|---|---|---|
| Model cache | > 90% | Pre-warm at startup; increase capacity |
| Prediction cache | > 60% | Normal for varied images; tune TTL |
| Dataset metadata cache | > 90% | Increase TTL if dataset rarely changes |

### Memory

- Keep process RSS below **800 MB** in production.
- Evict unused models with `force_cleanup()` during idle periods.
- Watch for monotone RSS growth in `detect_leaks` output — indicates a reference cycle or large allocation not being freed.

### Concurrency

- **10 workers**: baseline load; all operations should complete with error_rate = 0%.
- **50 workers**: moderate load; expect slight latency increase; error_rate should remain < 1%.
- **100 workers**: peak load; p95 will increase; aim for throughput > 50 rps on preprocessing.

---

## Report Interpretation

### JSON performance report

Generated by `generate_performance_report()` or `GET /api/v1/performance/summary`.

```json
{
  "report_type": "performance",
  "generated_at": "2024-07-14T12:00:00Z",
  "system": { "cpu_percent": 34.1, "ram_used_mb": 4096, ... },
  "inference": { "total_predictions": 142, "success_rate": 0.97, ... },
  "cache": { "model_cache": { "hit_rate": 0.9, ... }, "recommendations": [...] },
  "memory": { "current_rss_mb": 312.5, "warning_count": 0, ... },
  "api": { "total_endpoints_tracked": 5, "slow_endpoints": [...], ... },
  "profiler": { "total_functions": 8, "functions": { ... } },
  "concurrency": { "total_tests": 3, "results": [...] }
}
```

**Key fields to monitor:**

- `memory.warning_count > 0` — operations with RSS delta > 50 MB; investigate the operation listed in `memory.warnings`.
- `api.slow_endpoints` — endpoints with p95 > 500 ms; apply caching or optimize the handler.
- `cache.model_cache.hit_rate < 0.5` — follow the cache recommendations.
- `profiler.functions` — sorted by avg_ms descending; the top entry is the hottest code path.

### HTML report

Generated by `generate_html_report()` or `GET /api/v1/performance/report/html`.

The HTML report is self-contained (no external dependencies). Open it in any browser or serve it as a static file. It includes colour-coded tables for:

- System metrics (CPU, RAM, disk, process RSS)
- Inference metrics (success rate, avg/p95 latency)
- Model cache (hit rate, utilization)
- Memory deltas
- Top endpoints by latency
- Benchmark results
- Concurrency test results

### Benchmark report

| Status | Meaning |
|---|---|
| `ok` | Benchmark ran and produced valid statistics |
| `skipped` | Prerequisite absent (no model weights, no dataset) — not a failure |
| `error` | Exception raised during benchmark; check the `error` field |

**Throughput interpretation:**
- `preprocessing` > 50 rps — healthy
- `cache_get_hit` > 5,000 rps — healthy (in-memory LRU; should be near-instant)
- `single_inference` > 5 rps — acceptable for CPU-only inference

---

## API Reference

All endpoints require a valid JWT bearer token.

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/api/v1/performance/summary` | any | Full JSON report |
| GET | `/api/v1/performance/report/html` | any | Self-contained HTML report |
| GET | `/api/v1/performance/profiler?top=N` | any | Function timing summary |
| GET | `/api/v1/performance/memory` | any | Memory usage report |
| GET | `/api/v1/performance/cache` | any | Cache hit/miss report |
| GET | `/api/v1/performance/api-stats?slow_only=bool` | any | Per-endpoint latency |
| GET | `/api/v1/performance/concurrency` | any | Concurrency test history |
| POST | `/api/v1/performance/benchmark/run` | ADMIN/OPERATOR | Run benchmark suite |
| GET | `/api/v1/performance/benchmark/result` | any | Last benchmark result |
| POST | `/api/v1/performance/benchmark/single` | ADMIN/OPERATOR | Run one benchmark |
| DELETE | `/api/v1/performance/profiler/reset` | ADMIN | Clear all profiler data |

---

## Makefile Targets

All targets below are available from the **project root** (`make <target>`) and from **`ai-service/`** (`make -C ai-service <target>`).

```bash
make benchmark            # Quick benchmark (low iterations)
make benchmark-all        # Full benchmark (all modules, high iterations)
make profile              # CPU + memory profile of preprocessing, cache, metrics
make profile-api          # Live API latency stats from the optimizer singleton
make profile-training     # Profile training architecture build overhead
make stress-test          # Callable stress test: 10/50/100 concurrent workers
make stress-api           # HTTP stress test (requires dev server on :8000)
make memory-report        # Memory usage, leak detection, tracemalloc
make cache-report         # Cache hit rates, evictions, recommendations
make performance-report   # Save full JSON + HTML report to logs/performance/
make coverage             # Run tests with HTML + JSON coverage reports
```

### Example workflow

```bash
# 1. Start the dev server in a separate terminal
make dev-ai

# 2. Run a quick baseline benchmark
make benchmark

# 3. Profile the hottest paths
make profile

# 4. Check cache efficiency
make cache-report

# 5. Run stress tests at increasing concurrency
make stress-test

# 6. Check for memory leaks
make memory-report

# 7. Generate and save a full report
make performance-report   # → ai-service/logs/performance/performance_<ts>.html

# 8. Run the full test suite with coverage
make coverage             # → ai-service/htmlcov/index.html
```

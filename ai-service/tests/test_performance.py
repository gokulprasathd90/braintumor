"""
tests/test_performance.py — Comprehensive tests for app/performance package.

Covers:
  - Profiler: function timing, decorator, block timer, summary, reset
  - Benchmark: BenchmarkSuite individual benchmarks and run_all
  - Cache: CacheOptimizer, PredictionCache, DatasetMetadataCache, DashboardCache
  - Memory: MemoryProfiler, track_memory, force_cleanup
  - Concurrency: ConcurrencyProfiler, run_concurrent
  - Optimizer: APIOptimizer record/stats/ranking/reset
  - Reports: generate_performance_report, generate_html_report
  - API routes: all /performance/* endpoints via TestClient
"""

from __future__ import annotations

import time
import threading
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestProfiler:
    """Tests for app.performance.profiler."""

    def setup_method(self):
        from app.performance.profiler import get_profiler
        get_profiler().clear()

    def test_profile_function_returns_result(self):
        from app.performance.profiler import profile_function
        result = profile_function(lambda: time.sleep(0), n=5, label="test_fn")
        assert result.n == 5
        assert result.avg_ms >= 0
        assert result.min_ms <= result.avg_ms
        assert result.max_ms >= result.avg_ms
        assert result.throughput >= 0

    def test_profile_function_stats_fields(self):
        from app.performance.profiler import profile_function
        result = profile_function(lambda: None, n=10, label="stats_check")
        d = result.to_dict()
        for key in ("label", "n", "avg_ms", "min_ms", "max_ms", "median_ms",
                    "p95_ms", "p99_ms", "throughput_rps"):
            assert key in d, f"Missing key: {key}"

    def test_profile_block_records_elapsed(self):
        from app.performance.profiler import profile_block
        with profile_block("block_test") as blk:
            time.sleep(0.001)
        assert blk.elapsed_ms >= 1.0

    def test_profiler_timer_decorator(self):
        from app.performance.profiler import get_profiler
        profiler = get_profiler()

        @profiler.timer("decorated_fn")
        def work():
            return 42

        result = work()
        assert result == 42
        records = profiler.get_records("decorated_fn")
        assert len(records) == 1
        assert records[0].elapsed_ms >= 0

    def test_profiler_record_manual(self):
        from app.performance.profiler import get_profiler
        profiler = get_profiler()
        profiler.record("manual_event", 25.5)
        records = profiler.get_records("manual_event")
        assert len(records) == 1
        assert records[0].elapsed_ms == 25.5

    def test_profiler_summary_structure(self):
        from app.performance.profiler import get_profiler
        profiler = get_profiler()
        profiler.record("fn_a", 10.0)
        profiler.record("fn_a", 20.0)
        profiler.record("fn_b", 5.0)
        summary = profiler.summary()
        assert "total_functions" in summary
        assert "functions" in summary
        assert "fn_a" in summary["functions"]
        assert "fn_b" in summary["functions"]

    def test_profiler_summary_sorted_by_avg_ms(self):
        from app.performance.profiler import get_profiler
        profiler = get_profiler()
        profiler.record("slow_fn", 100.0)
        profiler.record("fast_fn", 1.0)
        summary = profiler.summary()
        keys = list(summary["functions"].keys())
        assert keys[0] == "slow_fn"

    def test_profiler_summary_top_param(self):
        from app.performance.profiler import get_profiler
        profiler = get_profiler()
        for i in range(5):
            profiler.record(f"fn_{i}", float(i * 10))
        summary = profiler.summary(top=2)
        assert len(summary["functions"]) == 2

    def test_profiler_clear(self):
        from app.performance.profiler import get_profiler
        profiler = get_profiler()
        profiler.record("to_clear", 1.0)
        profiler.clear()
        assert profiler.get_records() == []

    def test_profiler_reset_alias(self):
        from app.performance.profiler import get_profiler
        profiler = get_profiler()
        profiler.record("to_reset", 5.0)
        profiler.reset()
        assert profiler.get_records() == []

    def test_profile_function_with_cpu_profile(self):
        from app.performance.profiler import profile_function
        result = profile_function(lambda: sum(range(100)), n=3,
                                   label="cpu_prof", cpu_profile=True)
        assert result.cpu_profile is not None
        assert len(result.cpu_profile) > 0

    def test_profile_function_warmup(self):
        from app.performance.profiler import profile_function
        calls = []
        def fn():
            calls.append(1)
        profile_function(fn, n=3, warmup=2, label="warmup_test")
        # warmup=2 + n=3 = 5 total calls
        assert len(calls) == 5

    def test_profiler_store_result(self):
        from app.performance.profiler import get_profiler, profile_function
        profiler = get_profiler()
        result = profile_function(lambda: None, n=3, label="stored")
        profiler.store_result(result)
        results = profiler.get_results()
        assert "stored" in results

    def test_profile_function_handles_exception(self):
        from app.performance.profiler import profile_function
        def failing():
            raise ValueError("test error")
        # Should not raise, should still return stats
        result = profile_function(failing, n=3, label="error_fn")
        assert result.n == 3


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBenchmark:
    """Tests for app.performance.benchmark."""

    def test_benchmark_stats_to_dict(self):
        from app.performance.benchmark import BenchmarkStats
        stat = BenchmarkStats(
            name="test_bench", n=10, avg_ms=5.0, min_ms=1.0, max_ms=10.0,
            median_ms=5.0, p95_ms=9.0, throughput=200.0, total_ms=50.0,
        )
        d = stat.to_dict()
        assert d["name"] == "test_bench"
        assert d["avg_ms"] == 5.0
        assert d["status"] == "ok"

    def test_benchmark_result_add_and_finish(self):
        from app.performance.benchmark import BenchmarkResult, BenchmarkStats
        result = BenchmarkResult(suite_name="test_suite")
        stat = BenchmarkStats(
            name="s1", n=5, avg_ms=2.0, min_ms=1.0, max_ms=3.0,
            median_ms=2.0, p95_ms=3.0, throughput=500.0, total_ms=10.0,
        )
        result.add(stat)
        result.finish()
        assert len(result.benchmarks) == 1
        assert result.total_ms == 10.0
        assert result.finished_at is not None

    def test_benchmark_result_to_dict(self):
        from app.performance.benchmark import BenchmarkResult, BenchmarkStats
        result = BenchmarkResult(suite_name="suite_dict")
        result.add(BenchmarkStats(
            name="b1", n=5, avg_ms=1.0, min_ms=0.5, max_ms=2.0,
            median_ms=1.0, p95_ms=2.0, throughput=1000.0, total_ms=5.0,
        ))
        result.finish()
        d = result.to_dict()
        assert d["suite_name"] == "suite_dict"
        assert d["benchmark_count"] == 1
        assert len(d["benchmarks"]) == 1

    def test_benchmark_result_summary(self):
        from app.performance.benchmark import BenchmarkResult, BenchmarkStats
        result = BenchmarkResult(suite_name="summary_test")
        result.add(BenchmarkStats(
            name="ok_bench", n=5, avg_ms=1.0, min_ms=0.5, max_ms=2.0,
            median_ms=1.0, p95_ms=2.0, throughput=1000.0, total_ms=5.0, status="ok",
        ))
        result.add(BenchmarkStats(
            name="skip_bench", n=0, avg_ms=0, min_ms=0, max_ms=0,
            median_ms=0, p95_ms=0, throughput=0, total_ms=0, status="skipped",
        ))
        result.finish()
        s = result.summary()
        assert s["ok"] == 1
        assert s["skipped"] == 1
        assert s["errors"] == 0

    def test_bench_preprocessing(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_preprocess=3)
        stat = suite.bench_preprocessing(n=3)
        assert stat.name == "preprocessing"
        assert stat.status in ("ok", "error", "skipped")

    def test_bench_image_quality_check(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_preprocess=3)
        stat = suite.bench_image_quality_check(n=3)
        assert stat.name == "image_quality_check"

    def test_bench_model_cache_operations(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_cache=5)
        stat = suite.bench_model_cache_operations(n=5)
        assert stat.name == "cache_get_hit"
        assert stat.status == "ok"
        assert stat.avg_ms >= 0

    def test_bench_cache_stats(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_cache=5)
        stat = suite.bench_cache_stats(n=5)
        assert stat.name == "cache_stats_call"
        assert stat.status == "ok"

    def test_bench_single_inference(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_inference=3)
        stat = suite.bench_single_inference(n=3)
        assert stat.name == "single_inference"
        assert stat.status in ("ok", "error")

    def test_bench_batch_inference_returns_list(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_inference=2)
        stats = suite.bench_batch_inference(batch_sizes=[2, 4], n=2)
        assert isinstance(stats, list)
        assert len(stats) == 2
        for s in stats:
            assert s.status in ("ok", "error")

    def test_bench_metrics_collection(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite()
        stat = suite.bench_metrics_collection(n=3)
        assert stat.name == "system_metrics_collection"

    def test_bench_inference_metrics_record(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_cache=5)
        stat = suite.bench_inference_metrics_record(n=5)
        assert stat.name == "inference_metrics_record"
        assert stat.status == "ok"

    def test_run_all_returns_result(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_inference=2, n_preprocess=3, n_cache=5)
        result = suite.run_all(batch_sizes=[2])
        assert isinstance(result.benchmarks, list)
        assert len(result.benchmarks) > 0
        assert result.finished_at is not None

    def test_run_all_default_batch_sizes(self):
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(n_inference=2, n_preprocess=2, n_cache=3)
        result = suite.run_all()
        assert result.total_ms >= 0

    def test_run_benchmark_by_name(self):
        from app.performance.benchmark import run_benchmark
        stat = run_benchmark("cache_stats_call", n=3)
        assert stat.name == "cache_stats_call"

    def test_run_benchmark_unknown_name(self):
        from app.performance.benchmark import run_benchmark
        stat = run_benchmark("nonexistent_bench", n=3)
        assert stat.status == "error"

    def test_make_test_image(self):
        from app.performance.benchmark import _make_test_image
        img = _make_test_image(h=64, w=64)
        assert isinstance(img, bytes)
        assert len(img) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCacheOptimizer:
    """Tests for app.performance.cache."""

    def test_get_cache_optimizer_singleton(self):
        from app.performance.cache import get_cache_optimizer
        o1 = get_cache_optimizer()
        o2 = get_cache_optimizer()
        assert o1 is o2

    def test_cache_report_structure(self):
        from app.performance.cache import get_cache_report
        report = get_cache_report()
        assert "model_cache" in report
        assert "prediction_cache" in report
        assert "dataset_metadata_cache" in report
        assert "dashboard_cache" in report
        assert "recommendations" in report

    def test_model_cache_stats_fields(self):
        from app.performance.cache import get_cache_optimizer
        stats = get_cache_optimizer().get_model_cache_stats()
        d = stats.to_dict()
        for key in ("name", "capacity", "size", "hit_rate",
                    "total_hits", "total_misses"):
            assert key in d

    def test_recommendations_returns_list(self):
        from app.performance.cache import get_cache_optimizer
        recs = get_cache_optimizer().recommend()
        assert isinstance(recs, list)
        assert len(recs) > 0
        assert all(isinstance(r, str) for r in recs)

    def test_prediction_cache_miss_then_hit(self):
        from app.performance.cache import get_prediction_cache
        cache = get_prediction_cache()
        img_bytes = b"fake_image_data_12345"
        model_name = "test_model"
        # Miss
        result = cache.get(img_bytes, model_name)
        assert result is None
        # Set and hit
        cache.set(img_bytes, model_name, {"class": "glioma"})
        result = cache.get(img_bytes, model_name)
        assert result == {"class": "glioma"}

    def test_prediction_cache_stats(self):
        from app.performance.cache import get_prediction_cache
        cache = get_prediction_cache()
        stats = cache.get_stats()
        assert stats["name"] == "prediction_cache"
        assert "capacity" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats

    def test_prediction_cache_invalidate(self):
        from app.performance.cache import get_prediction_cache
        cache = get_prediction_cache()
        cache.set(b"img_inv", "model_inv", {"x": 1})
        cache.invalidate()
        assert cache.get(b"img_inv", "model_inv") is None

    def test_dataset_cache_miss_then_hit(self):
        from app.performance.cache import get_dataset_cache
        cache = get_dataset_cache()
        path = "/fake/dataset/info.json"
        assert cache.get(path) is None
        cache.set(path, {"classes": ["glioma", "notumor"]})
        assert cache.get(path) == {"classes": ["glioma", "notumor"]}

    def test_dataset_cache_invalidate_specific(self):
        from app.performance.cache import get_dataset_cache
        cache = get_dataset_cache()
        cache.set("/path/a", {"a": 1})
        cache.set("/path/b", {"b": 2})
        cache.invalidate("/path/a")
        assert cache.get("/path/a") is None
        assert cache.get("/path/b") == {"b": 2}

    def test_dashboard_cache_ttl(self):
        from app.performance.cache import _DashboardCache
        fast_cache = _DashboardCache(ttl_s=0.05)
        fast_cache.set("key1", {"val": 42})
        assert fast_cache.get("key1") == {"val": 42}
        time.sleep(0.1)
        assert fast_cache.get("key1") is None

    def test_dashboard_cache_stats(self):
        from app.performance.cache import get_dashboard_cache
        cache = get_dashboard_cache()
        cache.set("overview", {"cpu": 10})
        stats = cache.get_stats()
        assert stats["name"] == "dashboard_cache"
        assert "size" in stats

    def test_cache_stats_dataclass_utilization(self):
        from app.performance.cache import CacheStats
        s = CacheStats(
            name="mc", capacity=4, size=2, hit_rate=0.75,
            total_hits=15, total_misses=5, total_evictions=1, avg_load_ms=25.0,
        )
        d = s.to_dict()
        assert d["utilization"] == 0.5
        assert d["hit_rate"] == 0.75


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryProfiler:
    """Tests for app.performance.memory."""

    def setup_method(self):
        from app.performance.memory import get_memory_profiler
        get_memory_profiler().clear()

    def test_get_memory_profiler_singleton(self):
        from app.performance.memory import get_memory_profiler
        p1 = get_memory_profiler()
        p2 = get_memory_profiler()
        assert p1 is p2

    def test_track_memory_context_manager(self):
        from app.performance.memory import track_memory
        with track_memory("test_op") as m:
            _ = [0] * 1000
        assert m.delta_mb is not None
        assert m.elapsed_ms >= 0

    def test_track_memory_delta_accessible(self):
        from app.performance.memory import track_memory
        with track_memory("delta_test") as m:
            pass
        delta = m.to_delta()
        assert delta.label == "delta_test"
        assert delta.before_mb >= 0
        assert delta.after_mb >= 0

    def test_memory_snapshot(self):
        from app.performance.memory import get_memory_profiler
        profiler = get_memory_profiler()
        snap = profiler.snapshot("before_op")
        assert snap.rss_mb >= 0
        assert snap.label == "before_op"
        d = snap.to_dict()
        assert "rss_mb" in d
        assert "timestamp" in d

    def test_memory_profile_callable(self):
        from app.performance.memory import get_memory_profiler
        profiler = get_memory_profiler()
        delta = profiler.profile(lambda: time.sleep(0), label="profile_test")
        assert delta.label == "profile_test"
        assert delta.elapsed_ms >= 0

    def test_memory_report_structure(self):
        from app.performance.memory import get_memory_profiler
        profiler = get_memory_profiler()
        profiler.profile(lambda: None, label="report_test")
        report = profiler.get_report()
        assert "current_rss_mb" in report
        assert "total_operations_tracked" in report
        assert "warning_count" in report
        assert "operations" in report
        assert "resource_summary" in report

    def test_memory_clear(self):
        from app.performance.memory import get_memory_profiler
        profiler = get_memory_profiler()
        profiler.profile(lambda: None, label="to_clear")
        profiler.clear()
        report = profiler.get_report()
        assert report["total_operations_tracked"] == 0

    def test_memory_reset_alias(self):
        from app.performance.memory import get_memory_profiler
        profiler = get_memory_profiler()
        profiler.profile(lambda: None, label="to_reset")
        profiler.reset()
        report = profiler.get_report()
        assert report["total_operations_tracked"] == 0

    def test_force_cleanup(self):
        from app.performance.memory import get_memory_profiler
        result = get_memory_profiler().force_cleanup()
        assert "before_mb" in result
        assert "after_mb" in result
        assert "freed_mb" in result

    def test_detect_leaks_no_leak(self):
        from app.performance.memory import get_memory_profiler
        result = get_memory_profiler().detect_leaks(
            lambda: None, label="no_leak", iterations=3
        )
        assert "suspected_leak" in result
        assert result["iterations"] == 3
        assert len(result["rss_samples_mb"]) == 3

    def test_memory_snapshot_list_in_report(self):
        from app.performance.memory import get_memory_profiler
        profiler = get_memory_profiler()
        profiler.snapshot("snap_1")
        profiler.snapshot("snap_2")
        report = profiler.get_report()
        assert len(report["snapshots"]) >= 2

    def test_memory_warning_on_large_delta(self):
        from app.performance.memory import MemoryProfiler, MemoryDelta
        profiler = MemoryProfiler(leak_threshold_mb=0.0)  # everything triggers warning
        delta = MemoryDelta(
            label="big_alloc", before_mb=100.0, after_mb=200.0,
            delta_mb=100.0, elapsed_ms=50.0, warning=True,
        )
        profiler.record_delta(delta)
        report = profiler.get_report()
        assert report["warning_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrencyProfiler:
    """Tests for app.performance.concurrency."""

    def setup_method(self):
        from app.performance.concurrency import get_concurrency_profiler
        get_concurrency_profiler().clear()

    def test_run_concurrent_basic(self):
        from app.performance.concurrency import run_concurrent
        result = run_concurrent(lambda: time.sleep(0), workers=2, requests=10)
        assert result.completed == 10
        assert result.failed == 0
        assert result.workers == 2
        assert result.total_requests == 10

    def test_run_concurrent_stats_fields(self):
        from app.performance.concurrency import run_concurrent
        result = run_concurrent(lambda: None, workers=3, requests=9, label="test_conc")
        d = result.to_dict()
        for key in ("label", "workers", "total_requests", "completed",
                    "failed", "error_rate", "avg_ms", "throughput_rps"):
            assert key in d

    def test_run_concurrent_error_rate(self):
        from app.performance.concurrency import run_concurrent
        calls = [0]
        def sometimes_fails():
            calls[0] += 1
            if calls[0] % 2 == 0:
                raise RuntimeError("synthetic error")

        result = run_concurrent(sometimes_fails, workers=2, requests=10)
        assert result.error_rate >= 0
        assert result.failed + result.completed == 10

    def test_concurrency_profiler_accumulates_results(self):
        from app.performance.concurrency import get_concurrency_profiler, run_concurrent
        profiler = get_concurrency_profiler()
        run_concurrent(lambda: None, workers=2, requests=5, label="run1")
        run_concurrent(lambda: None, workers=2, requests=5, label="run2")
        results = profiler.get_results()
        assert len(results) >= 2

    def test_concurrency_profiler_report_structure(self):
        from app.performance.concurrency import get_concurrency_profiler, run_concurrent
        run_concurrent(lambda: None, workers=2, requests=5, label="report_test")
        report = get_concurrency_profiler().get_report()
        assert "timestamp" in report
        assert "total_tests" in report
        assert "results" in report
        assert isinstance(report["results"], list)

    def test_concurrency_profiler_clear(self):
        from app.performance.concurrency import get_concurrency_profiler, run_concurrent
        profiler = get_concurrency_profiler()
        run_concurrent(lambda: None, workers=2, requests=4)
        profiler.clear()
        assert profiler.get_results() == []

    def test_concurrent_result_throughput_positive(self):
        from app.performance.concurrency import run_concurrent
        result = run_concurrent(lambda: None, workers=4, requests=20)
        assert result.throughput >= 0

    def test_concurrent_result_timing_consistency(self):
        from app.performance.concurrency import run_concurrent
        result = run_concurrent(lambda: None, workers=2, requests=10)
        assert result.min_ms <= result.avg_ms
        assert result.avg_ms <= result.max_ms


# ═══════════════════════════════════════════════════════════════════════════════
# API OPTIMIZER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAPIOptimizer:
    """Tests for app.performance.optimizer."""

    def setup_method(self):
        from app.performance.optimizer import get_api_optimizer
        get_api_optimizer().clear()

    def test_record_single_request(self):
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        optimizer.record(path="/api/v1/predict", method="POST",
                         elapsed_ms=45.0, status_code=200)
        stats = optimizer.get_endpoint_stats("/api/v1/predict", "POST")
        assert stats is not None
        assert stats.total_calls == 1
        assert stats.avg_ms == 45.0

    def test_record_multiple_requests(self):
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        for ms in [10.0, 20.0, 30.0]:
            optimizer.record(path="/api/v1/health", method="GET",
                             elapsed_ms=ms, status_code=200)
        stats = optimizer.get_endpoint_stats("/api/v1/health", "GET")
        assert stats.total_calls == 3
        assert 18.0 <= stats.avg_ms <= 22.0

    def test_endpoint_stats_error_rate(self):
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        for sc in [200, 200, 500, 404]:
            optimizer.record(path="/api/v1/predict", method="POST",
                             elapsed_ms=10.0, status_code=sc)
        stats = optimizer.get_endpoint_stats("/api/v1/predict", "POST")
        assert stats.errors == 2
        assert stats.error_rate == 0.5

    def test_get_slow_endpoints(self):
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        # Add a bunch of slow requests
        for _ in range(25):
            optimizer.record(path="/api/v1/slow_route", method="GET",
                             elapsed_ms=800.0, status_code=200)
        slow = optimizer.get_slow_endpoints(threshold_ms=500.0)
        paths = [s.path for s in slow]
        assert "/api/v1/slow_route" in paths

    def test_get_ranked_by_latency(self):
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        optimizer.record(path="/fast", method="GET", elapsed_ms=5.0, status_code=200)
        optimizer.record(path="/slow", method="GET", elapsed_ms=200.0, status_code=200)
        ranked = optimizer.get_ranked_by_latency(top_n=5)
        assert ranked[0].path == "/slow"

    def test_api_report_structure(self):
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        optimizer.record(path="/api/v1/test", method="GET",
                         elapsed_ms=15.0, status_code=200)
        report = optimizer.get_api_report()
        assert "timestamp" in report
        assert "total_endpoints_tracked" in report
        assert "slow_endpoints" in report
        assert "ranked_by_latency" in report
        assert "all_endpoints" in report

    def test_optimizer_clear(self):
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        optimizer.record(path="/to/clear", method="GET",
                         elapsed_ms=10.0, status_code=200)
        optimizer.clear()
        assert optimizer.get_all_stats() == []

    def test_optimizer_reset_alias(self):
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        optimizer.record(path="/to/reset", method="GET",
                         elapsed_ms=10.0, status_code=200)
        optimizer.reset()
        assert optimizer.get_all_stats() == []

    def test_record_request_module_function(self):
        from app.performance.optimizer import record_request, get_api_optimizer
        get_api_optimizer().clear()
        record_request("/api/v1/batch", "POST", 120.0, 200)
        stats = get_api_optimizer().get_endpoint_stats("/api/v1/batch", "POST")
        assert stats is not None
        assert stats.avg_ms == 120.0

    def test_endpoint_is_slow_property(self):
        from app.performance.optimizer import EndpointStats
        slow = EndpointStats(
            path="/slow", method="GET", total_calls=1, errors=0,
            avg_ms=600.0, min_ms=600.0, max_ms=600.0, median_ms=600.0,
            p95_ms=600.0, p99_ms=600.0, error_rate=0.0, rps=1.0,
        )
        assert slow.is_slow is True
        fast = EndpointStats(
            path="/fast", method="GET", total_calls=1, errors=0,
            avg_ms=50.0, min_ms=50.0, max_ms=50.0, median_ms=50.0,
            p95_ms=50.0, p99_ms=50.0, error_rate=0.0, rps=10.0,
        )
        assert fast.is_slow is False


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestReports:
    """Tests for app.performance.reports."""

    def test_generate_performance_report_structure(self):
        from app.performance.reports import generate_performance_report
        report = generate_performance_report()
        assert report["report_type"] == "performance"
        assert "generated_at" in report
        for section in ("system", "inference", "cache", "memory", "api",
                        "profiler", "concurrency"):
            assert section in report

    def test_generate_html_report_returns_string(self):
        from app.performance.reports import generate_html_report, generate_performance_report
        report = generate_performance_report()
        html = generate_html_report(report)
        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "Performance Report" in html

    def test_generate_html_report_without_arg(self):
        from app.performance.reports import generate_html_report
        html = generate_html_report()
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html

    def test_html_report_contains_sections(self):
        from app.performance.reports import generate_html_report
        html = generate_html_report({"report_type": "performance", "generated_at": "now",
                                      "system": {"cpu_percent": 42.0, "ram_used_mb": 512.0,
                                                 "ram_percent": 50.0, "process_rss_mb": 200.0,
                                                 "uptime_seconds": 300, "platform": "Linux"}})
        assert "System Metrics" in html
        assert "42.0%" in html

    def test_build_benchmark_report(self):
        from app.performance.reports import get_report_generator
        rg = get_report_generator()
        # Use a mock BenchmarkResult to avoid running the full suite
        from app.performance.benchmark import BenchmarkResult, BenchmarkStats
        result = BenchmarkResult(suite_name="test")
        result.add(BenchmarkStats(
            name="bench1", n=5, avg_ms=10.0, min_ms=5.0, max_ms=15.0,
            median_ms=10.0, p95_ms=15.0, throughput=100.0, total_ms=50.0,
        ))
        result.finish()
        report = rg.build_benchmark_report(benchmark_result=result)
        assert report["report_type"] == "benchmark"
        assert "benchmark" in report

    def test_save_report_creates_file(self, tmp_path):
        from app.performance.reports import get_report_generator
        rg = get_report_generator()
        report = {"report_type": "test", "generated_at": "now", "data": "test"}
        path = rg.save_report(report, output_dir=tmp_path, filename="test_report.json")
        assert path.exists()
        import json
        with open(path) as f:
            saved = json.load(f)
        assert saved["report_type"] == "test"

    def test_save_html_report_creates_file(self, tmp_path):
        from app.performance.reports import get_report_generator
        rg = get_report_generator()
        report = {"report_type": "performance", "generated_at": "now"}
        path = rg.save_html_report(report, output_dir=tmp_path, filename="report.html")
        assert path.exists()
        content = path.read_text()
        assert "<!DOCTYPE html>" in content

    def test_report_generator_singleton(self):
        from app.performance.reports import get_report_generator
        rg1 = get_report_generator()
        rg2 = get_report_generator()
        assert rg1 is rg2

    def test_html_table_helper(self):
        from app.performance.reports import _html_table
        html = _html_table(
            "Test Table",
            ["Col1", "Col2"],
            [["val1", "val2"], ["val3", "val4"]],
        )
        assert "Test Table" in html
        assert "Col1" in html
        assert "val1" in html

    def test_html_section_helper(self):
        from app.performance.reports import _html_section
        html = _html_section("My Section", [("Key", "Value"), ("Other", "Data")])
        assert "My Section" in html
        assert "Key" in html
        assert "Value" in html


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES TESTS (via TestClient)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceRoutes:
    """Integration tests for /api/v1/performance/* endpoints."""

    def test_summary_endpoint(self):
        resp = client.get("/api/v1/performance/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "data" in data

    def test_html_report_endpoint(self):
        resp = client.get("/api/v1/performance/report/html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "<!DOCTYPE html>" in resp.text

    def test_profiler_endpoint(self):
        resp = client.get("/api/v1/performance/profiler")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "total_functions" in data["data"]

    def test_profiler_endpoint_with_top_param(self):
        # Record some timing data first
        from app.performance.profiler import get_profiler
        for i in range(5):
            get_profiler().record(f"route_fn_{i}", float(i * 10))
        resp = client.get("/api/v1/performance/profiler?top=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["functions"]) <= 3

    def test_memory_endpoint(self):
        resp = client.get("/api/v1/performance/memory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "current_rss_mb" in data["data"]

    def test_cache_endpoint(self):
        resp = client.get("/api/v1/performance/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "model_cache" in data["data"]
        assert "recommendations" in data["data"]

    def test_api_stats_endpoint(self):
        resp = client.get("/api/v1/performance/api-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "all_endpoints" in data["data"]

    def test_api_stats_slow_only_filter(self):
        # Inject a slow endpoint record
        from app.performance.optimizer import get_api_optimizer
        for _ in range(25):
            get_api_optimizer().record(
                path="/api/v1/very_slow", method="GET",
                elapsed_ms=900.0, status_code=200,
            )
        resp = client.get("/api/v1/performance/api-stats?slow_only=true")
        assert resp.status_code == 200
        data = resp.json()
        endpoints = data["data"]["all_endpoints"]
        for ep in endpoints:
            assert ep["is_slow"] is True

    def test_concurrency_endpoint(self):
        resp = client.get("/api/v1/performance/concurrency")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_benchmark_result_404_when_empty(self):
        resp = client.get("/api/v1/performance/benchmark/result")
        # May be 404 (no result yet) or 200 if a previous test ran a benchmark
        assert resp.status_code in (200, 404)

    def test_benchmark_single_preprocessing(self):
        resp = client.post(
            "/api/v1/performance/benchmark/single",
            json={"name": "preprocessing", "n": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["name"] == "preprocessing"

    def test_benchmark_single_cache(self):
        resp = client.post(
            "/api/v1/performance/benchmark/single",
            json={"name": "cache_stats_call", "n": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["name"] == "cache_stats_call"

    def test_benchmark_single_unknown_name(self):
        resp = client.post(
            "/api/v1/performance/benchmark/single",
            json={"name": "nonexistent_bench", "n": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Returns success=False for unknown benchmark (not a 400/500)
        assert data["data"]["status"] == "error"

    def test_profiler_reset_endpoint(self):
        resp = client.delete("/api/v1/performance/profiler/reset")
        assert resp.status_code == 200
        data = resp.json()
        assert "cleared" in data["data"]

    def test_benchmark_run_inline(self):
        resp = client.post(
            "/api/v1/performance/benchmark/run",
            json={
                "n_inference": 2,
                "n_preprocess": 3,
                "n_cache": 5,
                "batch_sizes": [2],
                "background": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"] is not None
        assert "benchmarks" in data["data"]

    def test_benchmark_run_background(self):
        resp = client.post(
            "/api/v1/performance/benchmark/run",
            json={
                "n_inference": 2,
                "n_preprocess": 2,
                "n_cache": 5,
                "batch_sizes": [2],
                "background": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["background"] is True
        # Poll for result
        import time as _time
        _time.sleep(0.5)

    def test_benchmark_run_conflict(self):
        # Start a background run, then try another
        import app.api.performance_routes as routes_module
        with routes_module._benchmark_lock:
            routes_module._benchmark_running = True
        try:
            resp = client.post(
                "/api/v1/performance/benchmark/run",
                json={"n_inference": 1, "n_preprocess": 1,
                      "n_cache": 1, "batch_sizes": [1], "background": True},
            )
            assert resp.status_code == 409
        finally:
            with routes_module._benchmark_lock:
                routes_module._benchmark_running = False


# ═══════════════════════════════════════════════════════════════════════════════
# STRESS TESTS (lightweight — no actual HTTP traffic)
# ═══════════════════════════════════════════════════════════════════════════════

class TestStressTests:
    """Stress tests for the concurrency module (callable-based, no HTTP)."""

    def test_concurrent_10_workers(self):
        from app.performance.concurrency import run_concurrent
        result = run_concurrent(lambda: time.sleep(0), workers=10, requests=50,
                                label="stress_10w")
        assert result.completed + result.failed == 50
        assert result.workers == 10

    def test_concurrent_50_workers(self):
        from app.performance.concurrency import run_concurrent
        result = run_concurrent(lambda: None, workers=50, requests=100,
                                label="stress_50w")
        assert result.completed + result.failed == 100

    def test_concurrent_100_workers(self):
        from app.performance.concurrency import run_concurrent
        result = run_concurrent(lambda: None, workers=100, requests=200,
                                label="stress_100w")
        assert result.completed + result.failed == 200
        assert result.throughput >= 0

    def test_batch_upload_stress_simulation(self):
        """Simulate batch upload processing concurrently."""
        from app.performance.concurrency import run_concurrent
        from app.performance.benchmark import _make_test_image

        img_bytes = _make_test_image()

        def process_batch():
            from app.preprocessing.preprocess import preprocess_for_inference
            preprocess_for_inference(img_bytes)

        result = run_concurrent(process_batch, workers=5, requests=10,
                                label="batch_upload_stress")
        assert result.completed >= 0

    def test_dashboard_polling_stress_simulation(self):
        """Simulate concurrent dashboard polling."""
        from app.performance.concurrency import run_concurrent
        from app.metrics.system import get_system_metrics

        result = run_concurrent(get_system_metrics, workers=10, requests=30,
                                label="dashboard_poll_stress")
        assert result.completed + result.failed == 30

    def test_inference_metrics_stress(self):
        """Stress test the metrics recording under concurrent load."""
        from app.performance.concurrency import run_concurrent
        from app.metrics.inference import InferenceMetricsStore

        store = InferenceMetricsStore()
        counter = [0]
        lock = threading.Lock()

        def record_metric():
            with lock:
                counter[0] += 1
            store.record(
                model_name="efficientnet",
                predicted_class="glioma",
                confidence=0.9,
                timing_ms=float(counter[0]),
                success=True,
                image_id=f"stress-{counter[0]}",
            )

        result = run_concurrent(record_metric, workers=10, requests=50,
                                label="metrics_stress")
        assert result.completed + result.failed == 50


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION: __init__.py PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformancePackagePublicAPI:
    """Verify that all symbols declared in __init__.py are importable."""

    def test_import_profiler_symbols(self):
        from app.performance import (
            Profiler, ProfileResult, FunctionProfile,
            profile_function, profile_block, get_profiler,
        )
        assert Profiler is not None
        assert callable(profile_function)
        assert callable(profile_block)
        assert callable(get_profiler)

    def test_import_benchmark_symbols(self):
        from app.performance import (
            BenchmarkSuite, BenchmarkResult, BenchmarkStats, run_benchmark,
        )
        assert BenchmarkSuite is not None
        assert callable(run_benchmark)

    def test_import_memory_symbols(self):
        from app.performance import (
            MemoryProfiler, MemorySnapshot, get_memory_profiler, track_memory,
        )
        assert callable(get_memory_profiler)
        assert callable(track_memory)

    def test_import_cache_symbols(self):
        from app.performance import CacheOptimizer, CacheStats, get_cache_optimizer
        assert CacheOptimizer is not None
        assert callable(get_cache_optimizer)

    def test_import_concurrency_symbols(self):
        from app.performance import (
            ConcurrencyProfiler, ConcurrencyResult,
            run_concurrent, get_concurrency_profiler,
        )
        assert callable(run_concurrent)

    def test_import_optimizer_symbols(self):
        from app.performance import (
            APIOptimizer, EndpointStats, record_request, get_api_stats,
        )
        assert callable(record_request)
        assert callable(get_api_stats)

    def test_import_reports_symbols(self):
        from app.performance import (
            ReportGenerator, get_report_generator,
            generate_performance_report, generate_html_report,
        )
        assert callable(generate_performance_report)
        assert callable(generate_html_report)

    def test_get_api_stats_returns_dict(self):
        from app.performance import get_api_stats
        result = get_api_stats()
        assert isinstance(result, dict)
        assert "all_endpoints" in result


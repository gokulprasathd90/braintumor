"""
app/performance/benchmark.py — Benchmark suite for all major modules.

Provides BenchmarkSuite which measures:
  - Single-image inference latency
  - Batch inference throughput
  - ZIP inference
  - Image preprocessing
  - Dataset metadata loading
  - Model cache operations
  - GradCAM generation
  - API endpoint response time

Each benchmark records: avg, min, max, median, p95, throughput, total runtime.

Usage
-----
    from app.performance.benchmark import BenchmarkSuite, run_benchmark

    suite = BenchmarkSuite()
    results = suite.run_all()          # all benchmarks
    result  = run_benchmark("preprocess", n=50)  # single benchmark
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.performance.profiler import ProfileResult, profile_function
from app.core.logging import logger


# ─── Benchmark registry ───────────────────────────────────────────────────────

@dataclass
class BenchmarkStats:
    """Full statistics for one benchmark run."""
    name:       str
    n:          int
    avg_ms:     float
    min_ms:     float
    max_ms:     float
    median_ms:  float
    p95_ms:     float
    throughput: float          # ops/second
    total_ms:   float
    status:     str = "ok"    # "ok" | "skipped" | "error"
    error:      Optional[str] = None
    timestamp:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra:      Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":       self.name,
            "n":          self.n,
            "avg_ms":     self.avg_ms,
            "min_ms":     self.min_ms,
            "max_ms":     self.max_ms,
            "median_ms":  self.median_ms,
            "p95_ms":     self.p95_ms,
            "throughput_rps": self.throughput,
            "total_ms":   self.total_ms,
            "status":     self.status,
            "error":      self.error,
            "timestamp":  self.timestamp,
            **self.extra,
        }


@dataclass
class BenchmarkResult:
    """Container for all benchmarks in one suite run."""
    suite_name:  str
    benchmarks:  List[BenchmarkStats] = field(default_factory=list)
    started_at:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None
    total_ms:    float = 0.0

    def add(self, stat: BenchmarkStats) -> None:
        self.benchmarks.append(stat)

    def finish(self) -> None:
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.total_ms = sum(b.total_ms for b in self.benchmarks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name":  self.suite_name,
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
            "total_ms":    self.total_ms,
            "benchmark_count": len(self.benchmarks),
            "benchmarks":  [b.to_dict() for b in self.benchmarks],
        }

    def summary(self) -> Dict[str, Any]:
        ok = [b for b in self.benchmarks if b.status == "ok"]
        skipped = [b for b in self.benchmarks if b.status == "skipped"]
        errors = [b for b in self.benchmarks if b.status == "error"]
        return {
            "suite_name": self.suite_name,
            "total": len(self.benchmarks),
            "ok": len(ok),
            "skipped": len(skipped),
            "errors": len(errors),
            "total_ms": self.total_ms,
        }


def _profile_to_stats(result: ProfileResult, name: str, **extra: Any) -> BenchmarkStats:
    return BenchmarkStats(
        name=name,
        n=result.n,
        avg_ms=result.avg_ms,
        min_ms=result.min_ms,
        max_ms=result.max_ms,
        median_ms=result.median_ms,
        p95_ms=result.p95_ms,
        throughput=result.throughput,
        total_ms=result.total_ms,
        extra=extra,
    )


def _make_test_image(h: int = 224, w: int = 224, seed: int = 42) -> bytes:
    """Create a synthetic PNG image for benchmarking (no disk I/O)."""
    import numpy as np
    import cv2
    rng = np.random.default_rng(seed)
    img = rng.integers(30, 200, (h, w, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("Failed to encode test image")
    return buf.tobytes()


def _skipped(name: str, reason: str) -> BenchmarkStats:
    return BenchmarkStats(
        name=name, n=0, avg_ms=0, min_ms=0, max_ms=0,
        median_ms=0, p95_ms=0, throughput=0, total_ms=0,
        status="skipped", error=reason,
    )


def _error_stat(name: str, exc: Exception) -> BenchmarkStats:
    return BenchmarkStats(
        name=name, n=0, avg_ms=0, min_ms=0, max_ms=0,
        median_ms=0, p95_ms=0, throughput=0, total_ms=0,
        status="error", error=f"{type(exc).__name__}: {exc}",
    )


# ─── BenchmarkSuite ───────────────────────────────────────────────────────────

class BenchmarkSuite:
    """
    Runs timed benchmarks across the major ai-service modules.

    Benchmarks that require trained model weights or a prepared dataset
    are gracefully skipped when the prerequisites are absent.

    Parameters
    ----------
    n_inference : int
        Iterations for inference benchmarks.
    n_preprocess : int
        Iterations for preprocessing benchmarks.
    n_cache : int
        Iterations for cache benchmarks.
    """

    def __init__(
        self,
        n_inference: int = 20,
        n_preprocess: int = 50,
        n_cache: int = 100,
    ) -> None:
        self.n_inference = n_inference
        self.n_preprocess = n_preprocess
        self.n_cache = n_cache

    # ── Individual benchmarks ─────────────────────────────────────────────────

    def bench_preprocessing(self, n: Optional[int] = None) -> BenchmarkStats:
        """Benchmark single-image spatial preprocessing pipeline."""
        n = n or self.n_preprocess
        try:
            img_bytes = _make_test_image()
            from app.preprocessing.preprocess import preprocess_for_inference
            result = profile_function(
                lambda: preprocess_for_inference(img_bytes),
                n=n, label="preprocessing",
            )
            return _profile_to_stats(result, "preprocessing",
                                      image_size=224, pipeline="denoise+clahe+resize+normalize")
        except Exception as exc:
            return _error_stat("preprocessing", exc)

    def bench_image_quality_check(self, n: Optional[int] = None) -> BenchmarkStats:
        """Benchmark image quality validation."""
        n = n or self.n_preprocess
        try:
            img_bytes = _make_test_image()
            from app.preprocessing.quality import validate_image_quality
            from app.preprocessing.config import DEFAULT_CONFIG
            result = profile_function(
                lambda: validate_image_quality(img_bytes, DEFAULT_CONFIG),
                n=n, label="quality_check",
            )
            return _profile_to_stats(result, "image_quality_check")
        except Exception as exc:
            return _error_stat("image_quality_check", exc)

    def bench_model_cache_operations(self, n: Optional[int] = None) -> BenchmarkStats:
        """Benchmark ModelCache get/hit operations (no disk load)."""
        n = n or self.n_cache
        try:
            from app.inference.cache import ModelCache, _CacheEntry
            from unittest.mock import MagicMock
            cache = ModelCache(capacity=4)
            fake_model = MagicMock()
            fake_model.count_params.return_value = 12_000_000
            entry = _CacheEntry(fake_model, "efficientnet", 50.0, {})
            with cache._lock:
                cache._store["efficientnet"] = entry

            result = profile_function(
                lambda: cache.get("efficientnet"),
                n=n, label="cache_hit",
            )
            return _profile_to_stats(result, "cache_get_hit",
                                      operation="get", cache_size=1)
        except Exception as exc:
            return _error_stat("cache_get_hit", exc)

    def bench_cache_stats(self, n: Optional[int] = None) -> BenchmarkStats:
        """Benchmark cache.stats() overhead."""
        n = n or self.n_cache
        try:
            from app.inference.cache import cache_stats
            result = profile_function(
                lambda: cache_stats(),
                n=n, label="cache_stats",
            )
            return _profile_to_stats(result, "cache_stats_call")
        except Exception as exc:
            return _error_stat("cache_stats_call", exc)

    def bench_single_inference(self, n: Optional[int] = None) -> BenchmarkStats:
        """Benchmark single-image inference with mocked model (no weights needed)."""
        n = n or self.n_inference
        try:
            from unittest.mock import MagicMock, patch
            import numpy as np
            from app.inference.config import InferenceConfig
            from app.inference.pipeline import InferencePipeline

            img_bytes = _make_test_image()
            fake_model = MagicMock()
            fake_model.predict.return_value = np.array(
                [[0.80, 0.10, 0.07, 0.03]], dtype=np.float32
            )
            fake_model.input_shape = (None, 224, 224, 3)

            cfg = InferenceConfig(
                model_name="efficientnet",
                class_names=["glioma", "meningioma", "notumor", "pituitary"],
                image_size=224,
            )
            pipeline = InferencePipeline(cfg)

            with patch("app.inference.pipeline.get_model", return_value=fake_model):
                result = profile_function(
                    lambda: pipeline.predict(img_bytes),
                    n=n, label="single_inference", warmup=2,
                )
            return _profile_to_stats(result, "single_inference",
                                      model="efficientnet", image_size=224)
        except Exception as exc:
            return _error_stat("single_inference", exc)

    def bench_batch_inference(
        self,
        batch_sizes: Optional[List[int]] = None,
        n: Optional[int] = None,
    ) -> List[BenchmarkStats]:
        """Benchmark batch inference for multiple batch sizes."""
        batch_sizes = batch_sizes or [4, 8, 16]
        n = n or max(5, self.n_inference // 4)
        stats_list: List[BenchmarkStats] = []

        for bs in batch_sizes:
            try:
                from unittest.mock import MagicMock, patch
                import numpy as np
                from app.inference.config import InferenceConfig
                from app.inference.pipeline import InferencePipeline

                sources = [(f"img_{i}.png", _make_test_image(seed=i)) for i in range(bs)]
                fake_model = MagicMock()
                fake_model.predict.return_value = np.array(
                    [[0.80, 0.10, 0.07, 0.03]], dtype=np.float32
                )
                fake_model.input_shape = (None, 224, 224, 3)

                cfg = InferenceConfig(
                    model_name="efficientnet",
                    class_names=["glioma", "meningioma", "notumor", "pituitary"],
                    image_size=224,
                    max_workers=2,
                )
                pipeline = InferencePipeline(cfg)

                with patch("app.inference.pipeline.get_model", return_value=fake_model):
                    with patch("app.inference.cache.get_model", return_value=fake_model):
                        result = profile_function(
                            lambda: pipeline.predict_batch(sources),
                            n=n, label=f"batch_{bs}",
                        )
                stat = _profile_to_stats(
                    result, f"batch_inference_bs{bs}",
                    batch_size=bs,
                    images_per_second=round(bs * result.throughput, 1),
                )
                stats_list.append(stat)
            except Exception as exc:
                stats_list.append(_error_stat(f"batch_inference_bs{bs}", exc))

        return stats_list

    def bench_dataset_metadata(self, n: Optional[int] = None) -> BenchmarkStats:
        """Benchmark dataset metadata loading."""
        n = n or self.n_preprocess
        try:
            from app.core.config import settings
            from app.dataset.metadata import dataset_info_exists
            if not dataset_info_exists(str(settings.dataset_processed_dir)):
                return _skipped("dataset_metadata", "No processed dataset found")

            from app.dataset.metadata import load_dataset_info
            result = profile_function(
                lambda: load_dataset_info(str(settings.dataset_processed_dir)),
                n=n, label="dataset_metadata",
            )
            return _profile_to_stats(result, "dataset_metadata_load")
        except Exception as exc:
            return _error_stat("dataset_metadata", exc)

    def bench_metrics_collection(self, n: Optional[int] = None) -> BenchmarkStats:
        """Benchmark system metrics collection."""
        n = n or 20
        try:
            from app.metrics.system import get_system_metrics
            result = profile_function(
                lambda: get_system_metrics(),
                n=n, label="system_metrics",
            )
            return _profile_to_stats(result, "system_metrics_collection")
        except Exception as exc:
            return _error_stat("system_metrics_collection", exc)

    def bench_inference_metrics_record(self, n: Optional[int] = None) -> BenchmarkStats:
        """Benchmark inference metrics recording throughput."""
        n = n or self.n_cache
        try:
            from app.metrics.inference import InferenceMetricsStore
            store = InferenceMetricsStore()

            result = profile_function(
                lambda: store.record(
                    model_name="efficientnet",
                    predicted_class="glioma",
                    confidence=0.85,
                    timing_ms=42.0,
                    success=True,
                    image_id="bench-id",
                ),
                n=n, label="metrics_record",
            )
            return _profile_to_stats(result, "inference_metrics_record")
        except Exception as exc:
            return _error_stat("inference_metrics_record", exc)

    # ── run_all ───────────────────────────────────────────────────────────────

    def run_all(self, batch_sizes: Optional[List[int]] = None) -> BenchmarkResult:
        """Run the full benchmark suite and return all results.

        Parameters
        ----------
        batch_sizes : list[int] | None
            Batch sizes to test in the batch-inference benchmark.
            Defaults to [4, 8, 16].
        """
        suite = BenchmarkResult(suite_name="full_suite")
        logger.info("[Benchmark] Starting full benchmark suite...")

        # Preprocessing
        suite.add(self.bench_preprocessing())
        suite.add(self.bench_image_quality_check())

        # Inference
        suite.add(self.bench_single_inference())
        for stat in self.bench_batch_inference(batch_sizes=batch_sizes):
            suite.add(stat)

        # Cache
        suite.add(self.bench_model_cache_operations())
        suite.add(self.bench_cache_stats())

        # Dataset
        suite.add(self.bench_dataset_metadata())

        # Metrics
        suite.add(self.bench_metrics_collection())
        suite.add(self.bench_inference_metrics_record())

        suite.finish()
        logger.info(
            f"[Benchmark] Suite complete | "
            f"{suite.summary()['ok']}/{suite.summary()['total']} benchmarks OK | "
            f"total={suite.total_ms:.0f}ms"
        )
        return suite


# ── Module-level convenience function ─────────────────────────────────────────

def run_benchmark(name: str, n: int = 10, **kwargs: Any) -> BenchmarkStats:
    """
    Run a single named benchmark from the suite.

    Available names: preprocessing, image_quality_check, single_inference,
    cache_get_hit, cache_stats_call, dataset_metadata, system_metrics_collection,
    inference_metrics_record
    """
    suite = BenchmarkSuite(n_inference=n, n_preprocess=n, n_cache=n)
    dispatch: Dict[str, Callable[[], BenchmarkStats]] = {
        "preprocessing":          suite.bench_preprocessing,
        "image_quality_check":    suite.bench_image_quality_check,
        "single_inference":       suite.bench_single_inference,
        "cache_get_hit":          suite.bench_model_cache_operations,
        "cache_stats_call":       suite.bench_cache_stats,
        "dataset_metadata":       suite.bench_dataset_metadata,
        "system_metrics":         suite.bench_metrics_collection,
        "inference_metrics":      suite.bench_inference_metrics_record,
    }
    fn = dispatch.get(name)
    if fn is None:
        available = list(dispatch.keys())
        return _error_stat(name, ValueError(f"Unknown benchmark '{name}'. Available: {available}"))
    return fn()

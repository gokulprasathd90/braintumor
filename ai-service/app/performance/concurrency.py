"""
app/performance/concurrency.py — Concurrent load and stress testing.

Provides:
  - ConcurrencyProfiler: run N workers hitting an endpoint or callable
  - run_concurrent: convenience function for concurrent load tests
  - StressTestRunner: drives HTTP stress tests at 10/50/100 concurrent users
  - ConcurrencyResult: statistics for a concurrent run

Usage
-----
    from app.performance.concurrency import run_concurrent, StressTestRunner

    # Concurrent callable test
    result = run_concurrent(lambda: my_fn(), workers=10, requests=100)

    # HTTP stress test
    runner = StressTestRunner(base_url="http://localhost:8000")
    report = runner.run_health_stress(workers=50, total_requests=500)
"""

from __future__ import annotations

import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.core.logging import logger


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class ConcurrencyResult:
    """Statistics for one concurrent load test."""
    label:           str
    workers:         int
    total_requests:  int
    completed:       int
    failed:          int
    error_rate:      float
    avg_ms:          float
    min_ms:          float
    max_ms:          float
    median_ms:       float
    p95_ms:          float
    p99_ms:          float
    throughput:      float         # requests/second
    total_elapsed_ms: float
    errors:          List[str] = field(default_factory=list)
    timestamp:       str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":           self.label,
            "workers":         self.workers,
            "total_requests":  self.total_requests,
            "completed":       self.completed,
            "failed":          self.failed,
            "error_rate":      self.error_rate,
            "avg_ms":          self.avg_ms,
            "min_ms":          self.min_ms,
            "max_ms":          self.max_ms,
            "median_ms":       self.median_ms,
            "p95_ms":          self.p95_ms,
            "p99_ms":          self.p99_ms,
            "throughput_rps":  self.throughput,
            "total_elapsed_ms": self.total_elapsed_ms,
            "sample_errors":   self.errors[:5],
            "timestamp":       self.timestamp,
        }


# ─── ConcurrencyProfiler ──────────────────────────────────────────────────────

class ConcurrencyProfiler:
    """
    Runs a callable concurrently from N threads and collects timing statistics.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._results: List[ConcurrencyResult] = []

    def run(
        self,
        fn: Callable[[], Any],
        *,
        label: str = "concurrent_test",
        workers: int = 10,
        total_requests: int = 100,
    ) -> ConcurrencyResult:
        """
        Execute *fn* from *workers* threads for *total_requests* total calls.

        Parameters
        ----------
        fn : callable
            Zero-argument callable to execute concurrently.
        label : str
            Human-readable test name.
        workers : int
            Thread pool size.
        total_requests : int
            Total number of fn() calls to make.

        Returns
        -------
        ConcurrencyResult
        """
        samples: List[float] = []
        errors: List[str] = []
        wall_start = time.perf_counter()

        def _call_once() -> float:
            t0 = time.perf_counter()
            fn()
            return (time.perf_counter() - t0) * 1000

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_call_once) for _ in range(total_requests)]
            for future in as_completed(futures):
                try:
                    ms = future.result(timeout=30)
                    samples.append(ms)
                except Exception as exc:
                    errors.append(f"{type(exc).__name__}: {exc}")

        wall_ms = (time.perf_counter() - wall_start) * 1000
        completed = len(samples)
        failed = len(errors)
        error_rate = round(failed / total_requests, 4) if total_requests > 0 else 0.0

        if samples:
            sorted_s = sorted(samples)
            n = len(sorted_s)
            avg = round(statistics.mean(samples), 2)
            p95 = round(sorted_s[int(n * 0.95)], 2) if n >= 20 else round(sorted_s[-1], 2)
            p99 = round(sorted_s[int(n * 0.99)], 2) if n >= 100 else round(sorted_s[-1], 2)
            throughput = round(completed / (wall_ms / 1000), 2) if wall_ms > 0 else 0.0
        else:
            avg = p95 = p99 = throughput = 0.0
            sorted_s = [0.0]

        result = ConcurrencyResult(
            label=label,
            workers=workers,
            total_requests=total_requests,
            completed=completed,
            failed=failed,
            error_rate=error_rate,
            avg_ms=avg,
            min_ms=round(sorted_s[0], 2) if sorted_s else 0.0,
            max_ms=round(sorted_s[-1], 2) if sorted_s else 0.0,
            median_ms=round(statistics.median(samples), 2) if samples else 0.0,
            p95_ms=p95,
            p99_ms=p99,
            throughput=throughput,
            total_elapsed_ms=round(wall_ms, 2),
            errors=errors[:20],
        )

        with self._lock:
            self._results.append(result)

        logger.info(
            f"[Concurrency] {label}: workers={workers} completed={completed} "
            f"failed={failed} avg={avg:.1f}ms throughput={throughput:.1f}rps"
        )
        return result

    def get_results(self) -> List[ConcurrencyResult]:
        with self._lock:
            return list(self._results)

    def get_report(self) -> Dict[str, Any]:
        with self._lock:
            results = list(self._results)
        return {
            "timestamp": _now_iso(),
            "total_tests": len(results),
            "results": [r.to_dict() for r in results],
        }

    def clear(self) -> None:
        with self._lock:
            self._results.clear()


# ─── StressTestRunner ─────────────────────────────────────────────────────────

class StressTestRunner:
    """
    HTTP-based stress tester using httpx.

    Runs configurable load profiles against the running FastAPI service.
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self._profiler = ConcurrencyProfiler()

    def _http_get(self, path: str, timeout: float = 10.0) -> None:
        """Make a single GET request. Raises on non-2xx or network error."""
        import httpx
        resp = httpx.get(f"{self.base_url}{path}", timeout=timeout)
        resp.raise_for_status()

    def _http_post_json(self, path: str, payload: Dict[str, Any], timeout: float = 30.0) -> None:
        import httpx
        resp = httpx.post(f"{self.base_url}{path}", json=payload, timeout=timeout)
        resp.raise_for_status()

    def _http_post_image(self, path: str, image_bytes: bytes, timeout: float = 30.0) -> None:
        import httpx
        resp = httpx.post(
            f"{self.base_url}{path}",
            files={"image": ("scan.png", image_bytes, "image/png")},
            timeout=timeout,
        )
        resp.raise_for_status()

    def run_health_stress(
        self,
        *,
        workers: int = 10,
        total_requests: int = 100,
    ) -> ConcurrencyResult:
        """Stress-test the /health endpoint."""
        return self._profiler.run(
            lambda: self._http_get("/api/v1/health"),
            label=f"health_stress_w{workers}",
            workers=workers,
            total_requests=total_requests,
        )

    def run_predict_stress(
        self,
        *,
        workers: int = 10,
        total_requests: int = 50,
        image_bytes: Optional[bytes] = None,
    ) -> ConcurrencyResult:
        """Stress-test the /predict/image endpoint."""
        if image_bytes is None:
            from app.performance.benchmark import _make_test_image
            image_bytes = _make_test_image()
        return self._profiler.run(
            lambda: self._http_post_image("/api/v1/predict/image", image_bytes),
            label=f"predict_stress_w{workers}",
            workers=workers,
            total_requests=total_requests,
        )

    def run_dashboard_stress(
        self,
        *,
        workers: int = 20,
        total_requests: int = 200,
    ) -> ConcurrencyResult:
        """Stress-test the /dashboard/overview endpoint."""
        return self._profiler.run(
            lambda: self._http_get("/api/v1/dashboard/overview"),
            label=f"dashboard_stress_w{workers}",
            workers=workers,
            total_requests=total_requests,
        )

    def run_full_stress_suite(
        self,
        worker_levels: Optional[List[int]] = None,
    ) -> List[ConcurrencyResult]:
        """
        Run health + dashboard stress tests at multiple concurrency levels.

        Parameters
        ----------
        worker_levels : list[int] | None
            Concurrency levels to test. Defaults to [10, 50, 100].
        """
        worker_levels = worker_levels or [10, 50, 100]
        results: List[ConcurrencyResult] = []

        for w in worker_levels:
            requests = w * 10  # 10x workers
            logger.info(f"[Stress] Running health stress: workers={w} requests={requests}")
            results.append(self.run_health_stress(workers=w, total_requests=requests))

        logger.info("[Stress] Running dashboard stress: workers=20 requests=200")
        results.append(self.run_dashboard_stress(workers=20, total_requests=200))

        return results

    def get_report(self) -> Dict[str, Any]:
        return self._profiler.get_report()


# ── Singletons ────────────────────────────────────────────────────────────────
_concurrency_profiler = ConcurrencyProfiler()


def get_concurrency_profiler() -> ConcurrencyProfiler:
    return _concurrency_profiler


def run_concurrent(
    fn: Callable[[], Any],
    *,
    workers: int = 10,
    requests: int = 100,
    label: str = "concurrent",
) -> ConcurrencyResult:
    """Convenience wrapper: run *fn* concurrently with *workers* threads."""
    return _concurrency_profiler.run(
        fn, label=label, workers=workers, total_requests=requests
    )

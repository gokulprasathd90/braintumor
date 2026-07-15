"""
app/performance/profiler.py — CPU, memory, and function-level profiling.

Provides:
  - Profiler: context-manager and decorator-based function/block timing
  - profile_function: time a callable N times and return statistics
  - profile_block: context-manager returning elapsed time
  - CPU profiling via cProfile
  - Memory profiling via tracemalloc
  - Per-module execution tracing

Usage
-----
    from app.performance.profiler import profile_function, profile_block, get_profiler

    # Decorator timing
    @get_profiler().timer("my_function")
    def expensive():
        ...

    # Block timing
    with profile_block("preprocessing") as blk:
        result = preprocess_image(bytes_data)
    print(f"Took {blk.elapsed_ms:.1f}ms")

    # Benchmark a callable N times
    stats = profile_function(lambda: preprocess_image(data), n=100, label="preprocess")
"""

from __future__ import annotations

import cProfile
import functools
import io
import pstats
import threading
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generator, List, Optional

from app.core.logging import logger


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class FunctionProfile:
    """Timing record for one function invocation."""
    label:       str
    elapsed_ms:  float
    timestamp:   str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":      self.label,
            "elapsed_ms": self.elapsed_ms,
            "timestamp":  self.timestamp,
            **self.extra,
        }


@dataclass
class ProfileResult:
    """Aggregate statistics across N invocations of a function."""
    label:        str
    n:            int
    total_ms:     float
    avg_ms:       float
    min_ms:       float
    max_ms:       float
    median_ms:    float
    p95_ms:       float
    p99_ms:       float
    throughput:   float            # calls per second
    all_ms:       List[float] = field(default_factory=list, repr=False)
    cpu_profile:  Optional[str] = None   # cProfile text output
    mem_before_mb: Optional[float] = None
    mem_after_mb:  Optional[float] = None
    mem_delta_mb:  Optional[float] = None
    timestamp:    str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":        self.label,
            "n":            self.n,
            "total_ms":     self.total_ms,
            "avg_ms":       self.avg_ms,
            "min_ms":       self.min_ms,
            "max_ms":       self.max_ms,
            "median_ms":    self.median_ms,
            "p95_ms":       self.p95_ms,
            "p99_ms":       self.p99_ms,
            "throughput_rps": self.throughput,
            "mem_before_mb": self.mem_before_mb,
            "mem_after_mb":  self.mem_after_mb,
            "mem_delta_mb":  self.mem_delta_mb,
            "timestamp":    self.timestamp,
        }


def _compute_stats(samples: List[float], label: str, cpu_profile: Optional[str] = None,
                   mem_before: Optional[float] = None, mem_after: Optional[float] = None) -> ProfileResult:
    """Compute aggregate statistics from a list of elapsed-ms samples."""
    if not samples:
        raise ValueError("No samples to compute stats from")

    n = len(samples)
    total = sum(samples)
    avg = total / n
    sorted_s = sorted(samples)
    median = sorted_s[n // 2]
    p95 = sorted_s[int(n * 0.95)] if n >= 20 else sorted_s[-1]
    p99 = sorted_s[int(n * 0.99)] if n >= 100 else sorted_s[-1]
    throughput = round(1000 / avg, 2) if avg > 0 else 0.0

    mem_delta = round(mem_after - mem_before, 2) if (mem_before is not None and mem_after is not None) else None

    return ProfileResult(
        label=label,
        n=n,
        total_ms=round(total, 2),
        avg_ms=round(avg, 2),
        min_ms=round(sorted_s[0], 2),
        max_ms=round(sorted_s[-1], 2),
        median_ms=round(median, 2),
        p95_ms=round(p95, 2),
        p99_ms=round(p99, 2),
        throughput=throughput,
        all_ms=samples,
        cpu_profile=cpu_profile,
        mem_before_mb=mem_before,
        mem_after_mb=mem_after,
        mem_delta_mb=mem_delta,
    )


# ─── Context manager block timer ──────────────────────────────────────────────

class _BlockTimer:
    """Returned by profile_block(); holds elapsed time after context exits."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "_BlockTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
        logger.debug(f"[Profiler] {self.label} took {self.elapsed_ms:.2f}ms")


@contextmanager
def profile_block(label: str) -> Generator[_BlockTimer, None, None]:
    """Context-manager that measures elapsed wall time of a block.

    Usage::

        with profile_block("my_block") as b:
            do_work()
        print(b.elapsed_ms)
    """
    timer = _BlockTimer(label)
    with timer:
        yield timer


# ─── profile_function ─────────────────────────────────────────────────────────

def profile_function(
    fn: Callable[[], Any],
    *,
    n: int = 10,
    label: str = "function",
    warmup: int = 1,
    cpu_profile: bool = False,
    memory_profile: bool = False,
) -> ProfileResult:
    """
    Time *fn* for *n* iterations and return aggregate statistics.

    Parameters
    ----------
    fn : callable
        Zero-argument callable to benchmark.
    n : int
        Number of timed iterations (default 10).
    label : str
        Human-readable label for reports.
    warmup : int
        Untimed warm-up iterations run before timing begins (default 1).
    cpu_profile : bool
        Capture a cProfile snapshot during the timed run.
    memory_profile : bool
        Capture tracemalloc memory before/after the timed run.

    Returns
    -------
    ProfileResult
    """
    # Warm-up
    for _ in range(warmup):
        try:
            fn()
        except Exception:
            pass

    cpu_text: Optional[str] = None
    mem_before: Optional[float] = None
    mem_after: Optional[float] = None

    # Memory baseline
    if memory_profile:
        try:
            import psutil, os
            proc = psutil.Process(os.getpid())
            mem_before = round(proc.memory_info().rss / 1024 / 1024, 2)
        except Exception:
            pass

    # CPU profiler (wraps all n iterations)
    pr: Optional[cProfile.Profile] = None
    if cpu_profile:
        pr = cProfile.Profile()
        pr.enable()

    samples: List[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            fn()
        except Exception as exc:
            logger.warning(f"[Profiler] {label} iteration raised: {exc}")
        elapsed = (time.perf_counter() - t0) * 1000
        samples.append(elapsed)

    if pr is not None:
        pr.disable()
        buf = io.StringIO()
        ps = pstats.Stats(pr, stream=buf).sort_stats("cumulative")
        ps.print_stats(20)  # top 20 lines
        cpu_text = buf.getvalue()

    # Memory after
    if memory_profile:
        try:
            import psutil, os
            proc = psutil.Process(os.getpid())
            mem_after = round(proc.memory_info().rss / 1024 / 1024, 2)
        except Exception:
            pass

    result = _compute_stats(samples, label, cpu_text, mem_before, mem_after)
    logger.info(
        f"[Profiler] {label}: n={n} avg={result.avg_ms:.1f}ms "
        f"p95={result.p95_ms:.1f}ms throughput={result.throughput:.1f}rps"
    )
    return result


# ─── Profiler class ───────────────────────────────────────────────────────────

class Profiler:
    """
    Process-wide profiler that accumulates timing records and generates reports.

    Thread-safe via RLock.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: List[FunctionProfile] = []
        self._results: Dict[str, ProfileResult] = {}

    def timer(self, label: str) -> Callable:
        """Decorator: record elapsed time of the wrapped function on each call."""
        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                t0 = time.perf_counter()
                result = fn(*args, **kwargs)
                elapsed = (time.perf_counter() - t0) * 1000
                record = FunctionProfile(label=label, elapsed_ms=elapsed)
                with self._lock:
                    self._records.append(record)
                return result
            return wrapper
        return decorator

    def record(self, label: str, elapsed_ms: float, **extra: Any) -> None:
        """Manually record a timing event."""
        with self._lock:
            self._records.append(FunctionProfile(
                label=label,
                elapsed_ms=elapsed_ms,
                extra=extra,
            ))

    def store_result(self, result: ProfileResult) -> None:
        """Store a ProfileResult for later reporting."""
        with self._lock:
            self._results[result.label] = result

    def get_records(self, label: Optional[str] = None) -> List[FunctionProfile]:
        with self._lock:
            if label:
                return [r for r in self._records if r.label == label]
            return list(self._records)

    def get_results(self) -> Dict[str, ProfileResult]:
        with self._lock:
            return dict(self._results)

    def summary(self, top: Optional[int] = None) -> Dict[str, Any]:
        """Return a per-label aggregate summary of all recorded timings.

        Parameters
        ----------
        top : int | None
            If specified, return only the *top* slowest functions by avg_ms.
        """
        with self._lock:
            by_label: Dict[str, List[float]] = {}
            for r in self._records:
                by_label.setdefault(r.label, []).append(r.elapsed_ms)

        summary_data: Dict[str, Any] = {}
        for lbl, samples in by_label.items():
            result = _compute_stats(samples, lbl)
            summary_data[lbl] = result.to_dict()

        # Sort by avg_ms descending
        sorted_items = sorted(
            summary_data.items(),
            key=lambda kv: kv[1].get("avg_ms", 0),
            reverse=True,
        )
        if top is not None:
            sorted_items = sorted_items[:top]

        return {
            "total_functions": len(by_label),
            "functions": {k: v for k, v in sorted_items},
        }

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._results.clear()

    def reset(self) -> None:
        """Alias for clear() — wipe all accumulated profiling data."""
        self.clear()

    def profile_tracemalloc(
        self, fn: Callable[[], Any], *, label: str = "tracemalloc"
    ) -> Dict[str, Any]:
        """Profile peak memory allocation of *fn* using tracemalloc."""
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()
        t0 = time.perf_counter()
        try:
            fn()
        except Exception as exc:
            logger.warning(f"[Profiler] tracemalloc target raised: {exc}")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_kb = sum(s.size_diff for s in top_stats) / 1024

        top_lines = [
            {
                "file": str(s.traceback[0].filename).split("ai-service")[-1],
                "line": s.traceback[0].lineno,
                "size_kb": round(s.size_diff / 1024, 2),
            }
            for s in top_stats[:10]
            if s.size_diff > 0
        ]

        return {
            "label": label,
            "elapsed_ms": round(elapsed_ms, 2),
            "total_allocated_kb": round(total_kb, 2),
            "top_allocations": top_lines,
        }


# ── Process-wide singleton ─────────────────────────────────────────────────────
_profiler = Profiler()


def get_profiler() -> Profiler:
    """Return the process-wide Profiler singleton."""
    return _profiler

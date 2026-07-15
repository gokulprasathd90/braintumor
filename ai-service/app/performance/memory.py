"""
app/performance/memory.py — Memory profiling, leak detection, and cleanup.

Provides:
  - MemorySnapshot: point-in-time memory measurement
  - MemoryProfiler: track memory across multiple operations, detect leaks
  - track_memory: context-manager that records memory delta
  - get_memory_report: full memory report for all tracked operations

Usage
-----
    from app.performance.memory import MemoryProfiler, track_memory, get_memory_profiler

    # Context manager
    with track_memory("batch_inference") as m:
        result = runner.run(sources)
    print(f"Memory delta: {m.delta_mb:.1f}MB")

    # Full report
    report = get_memory_profiler().get_report()
"""

from __future__ import annotations

import gc
import os
import threading
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generator, List, Optional

from app.core.logging import logger


def _get_process_rss_mb() -> float:
    """Return current process RSS in MB using psutil."""
    try:
        import psutil
        return round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)
    except Exception:
        return 0.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Snapshot ────────────────────────────────────────────────────────────────

@dataclass
class MemorySnapshot:
    """A point-in-time memory measurement."""
    label:         str
    rss_mb:        float        # process resident set size
    timestamp:     str = field(default_factory=_now_iso)
    tracemalloc_kb: Optional[float] = None   # tracemalloc current, if active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":          self.label,
            "rss_mb":         self.rss_mb,
            "tracemalloc_kb": self.tracemalloc_kb,
            "timestamp":      self.timestamp,
        }


@dataclass
class MemoryDelta:
    """Memory change between two snapshots."""
    label:      str
    before_mb:  float
    after_mb:   float
    delta_mb:   float
    elapsed_ms: float
    timestamp:  str = field(default_factory=_now_iso)
    warning:    bool = False    # True when delta_mb exceeds threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":      self.label,
            "before_mb":  self.before_mb,
            "after_mb":   self.after_mb,
            "delta_mb":   self.delta_mb,
            "elapsed_ms": self.elapsed_ms,
            "warning":    self.warning,
            "timestamp":  self.timestamp,
        }


# ─── Context manager helper ───────────────────────────────────────────────────

class _MemoryTracker:
    """Returned by track_memory(); holds delta after context exits."""

    def __init__(self, label: str, leak_threshold_mb: float = 50.0) -> None:
        self.label = label
        self.leak_threshold_mb = leak_threshold_mb
        self.before_mb: float = 0.0
        self.after_mb:  float = 0.0
        self.delta_mb:  float = 0.0
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "_MemoryTracker":
        gc.collect()
        self.before_mb = _get_process_rss_mb()
        import time
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        import time
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
        gc.collect()
        self.after_mb = _get_process_rss_mb()
        self.delta_mb = round(self.after_mb - self.before_mb, 2)
        if self.delta_mb > self.leak_threshold_mb:
            logger.warning(
                f"[Memory] {self.label}: large memory growth "
                f"{self.delta_mb:.1f}MB (threshold: {self.leak_threshold_mb}MB)"
            )
        logger.debug(
            f"[Memory] {self.label}: {self.before_mb:.1f}→{self.after_mb:.1f}MB "
            f"(Δ{self.delta_mb:+.1f}MB) in {self.elapsed_ms:.0f}ms"
        )

    def to_delta(self) -> MemoryDelta:
        return MemoryDelta(
            label=self.label,
            before_mb=self.before_mb,
            after_mb=self.after_mb,
            delta_mb=self.delta_mb,
            elapsed_ms=self.elapsed_ms,
            warning=(self.delta_mb > self.leak_threshold_mb),
        )


@contextmanager
def track_memory(label: str, *, leak_threshold_mb: float = 50.0) -> Generator[_MemoryTracker, None, None]:
    """Context-manager that measures memory change around a block.

    Usage::

        with track_memory("my_op") as m:
            do_work()
        print(m.delta_mb)
    """
    tracker = _MemoryTracker(label, leak_threshold_mb)
    with tracker:
        yield tracker


# ─── MemoryProfiler ───────────────────────────────────────────────────────────

class MemoryProfiler:
    """
    Accumulates memory delta records and generates reports.

    Thread-safe via RLock.
    """

    def __init__(self, leak_threshold_mb: float = 50.0) -> None:
        self._lock = threading.RLock()
        self._deltas: List[MemoryDelta] = []
        self._snapshots: List[MemorySnapshot] = []
        self._leak_threshold = leak_threshold_mb

    def snapshot(self, label: str) -> MemorySnapshot:
        """Take a labelled memory snapshot and record it."""
        rss = _get_process_rss_mb()
        tm_kb: Optional[float] = None
        try:
            if tracemalloc.is_tracing():
                current, _ = tracemalloc.get_traced_memory()
                tm_kb = round(current / 1024, 2)
        except Exception:
            pass
        snap = MemorySnapshot(label=label, rss_mb=rss, tracemalloc_kb=tm_kb)
        with self._lock:
            self._snapshots.append(snap)
        return snap

    def record_delta(self, delta: MemoryDelta) -> None:
        with self._lock:
            self._deltas.append(delta)

    def profile(self, fn: Callable[[], Any], *, label: str = "operation") -> MemoryDelta:
        """Profile memory growth of *fn* and record the delta."""
        tracker = _MemoryTracker(label, self._leak_threshold)
        with tracker:
            try:
                fn()
            except Exception as exc:
                logger.warning(f"[MemoryProfiler] {label} raised: {exc}")
        delta = tracker.to_delta()
        self.record_delta(delta)
        return delta

    def profile_tracemalloc(
        self, fn: Callable[[], Any], *, label: str = "tracemalloc_profile"
    ) -> Dict[str, Any]:
        """Profile allocation hotspots using tracemalloc."""
        gc.collect()
        tracemalloc.start()
        snap_before = tracemalloc.take_snapshot()
        import time
        t0 = time.perf_counter()
        try:
            fn()
        except Exception as exc:
            logger.warning(f"[MemoryProfiler] tracemalloc {label} raised: {exc}")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        snap_after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        gc.collect()

        stats = snap_after.compare_to(snap_before, "lineno")
        total_kb = sum(max(0, s.size_diff) for s in stats) / 1024
        top = [
            {
                "file": str(s.traceback[0].filename).split("site-packages")[-1].lstrip("/\\"),
                "line": s.traceback[0].lineno,
                "size_kb": round(s.size_diff / 1024, 2),
            }
            for s in stats[:15]
            if s.size_diff > 1024  # only > 1 KB
        ]
        return {
            "label": label,
            "elapsed_ms": round(elapsed_ms, 2),
            "total_allocated_kb": round(total_kb, 2),
            "top_allocations": top,
        }

    def detect_leaks(self, fn: Callable[[], Any], *, label: str = "leak_test",
                     iterations: int = 5) -> Dict[str, Any]:
        """
        Run *fn* N times and check whether RSS grows monotonically.

        A growing RSS across all iterations suggests a memory leak.
        """
        gc.collect()
        snapshots: List[float] = []
        for _ in range(iterations):
            fn()
            gc.collect()
            snapshots.append(_get_process_rss_mb())

        deltas = [snapshots[i] - snapshots[i - 1] for i in range(1, len(snapshots))]
        monotone_growth = all(d >= 0 for d in deltas)
        total_growth = snapshots[-1] - snapshots[0] if snapshots else 0.0
        suspected_leak = monotone_growth and total_growth > 5.0  # > 5MB monotone growth

        return {
            "label": label,
            "iterations": iterations,
            "rss_samples_mb": snapshots,
            "deltas_mb": [round(d, 2) for d in deltas],
            "total_growth_mb": round(total_growth, 2),
            "monotone_growth": monotone_growth,
            "suspected_leak": suspected_leak,
        }

    def force_cleanup(self) -> Dict[str, Any]:
        """Force garbage collection and clear TF/Keras caches where possible."""
        before_mb = _get_process_rss_mb()

        # Python GC
        gc.collect()
        gc.collect()
        gc.collect()

        # Clear inference model cache
        try:
            from app.inference.cache import _cache
            evicted = len(_cache)
            _cache.clear()
        except Exception:
            evicted = 0

        after_mb = _get_process_rss_mb()
        freed_mb = round(before_mb - after_mb, 2)

        logger.info(
            f"[Memory] Cleanup: before={before_mb:.1f}MB after={after_mb:.1f}MB "
            f"freed={freed_mb:.1f}MB models_evicted={evicted}"
        )
        return {
            "before_mb": before_mb,
            "after_mb":  after_mb,
            "freed_mb":  freed_mb,
            "models_evicted": evicted,
        }

    def get_report(self) -> Dict[str, Any]:
        """Return a complete memory report."""
        with self._lock:
            deltas = list(self._deltas)
            snaps = list(self._snapshots)

        rss = _get_process_rss_mb()
        warnings = [d.to_dict() for d in deltas if d.warning]

        return {
            "timestamp": _now_iso(),
            "current_rss_mb": rss,
            "total_operations_tracked": len(deltas),
            "warning_count": len(warnings),
            "warnings": warnings,
            "operations": [d.to_dict() for d in deltas[-50:]],  # last 50
            "snapshots": [s.to_dict() for s in snaps[-20:]],    # last 20
            "resource_summary": _get_resource_summary(),
        }

    def clear(self) -> None:
        with self._lock:
            self._deltas.clear()
            self._snapshots.clear()

    def reset(self) -> None:
        """Alias for clear() — wipe all accumulated memory profiling data."""
        self.clear()


def _get_resource_summary() -> Dict[str, Any]:
    """Collect a summary of current resource utilisation."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "ram_total_mb":     round(vm.total / 1024 / 1024, 1),
            "ram_used_mb":      round(vm.used / 1024 / 1024, 1),
            "ram_available_mb": round(vm.available / 1024 / 1024, 1),
            "ram_percent":      round(vm.percent, 1),
            "process_rss_mb":   _get_process_rss_mb(),
        }
    except Exception:
        return {"process_rss_mb": _get_process_rss_mb()}


# ── Singleton ─────────────────────────────────────────────────────────────────
_memory_profiler = MemoryProfiler()


def get_memory_profiler() -> MemoryProfiler:
    """Return the process-wide MemoryProfiler singleton."""
    return _memory_profiler

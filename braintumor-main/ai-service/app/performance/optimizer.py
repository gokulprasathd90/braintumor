"""
app/performance/optimizer.py — API response-time tracking and optimization.

Records per-endpoint latency on every request and provides:
  - EndpointStats: per-path metrics (avg, p95, error rate, RPS)
  - Slow endpoint detection
  - Endpoint ranking by latency
  - Middleware integration hook (record_request)

Usage
-----
    from app.performance.optimizer import record_request, get_api_stats

    # Call from FastAPI middleware after each request
    record_request(path="/api/v1/predict", method="POST",
                   elapsed_ms=42.5, status_code=200)

    stats = get_api_stats()
"""

from __future__ import annotations

import statistics
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from app.core.logging import logger


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── EndpointStats ────────────────────────────────────────────────────────────

@dataclass
class EndpointStats:
    """Aggregate performance metrics for one API path."""
    path:         str
    method:       str
    total_calls:  int
    errors:       int
    avg_ms:       float
    min_ms:       float
    max_ms:       float
    median_ms:    float
    p95_ms:       float
    p99_ms:       float
    error_rate:   float
    rps:          float       # requests per second (over tracked window)
    timestamp:    str = field(default_factory=_now_iso)

    @property
    def is_slow(self) -> bool:
        """True when p95 latency exceeds 500ms."""
        return self.p95_ms > 500.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path":        self.path,
            "method":      self.method,
            "total_calls": self.total_calls,
            "errors":      self.errors,
            "avg_ms":      self.avg_ms,
            "min_ms":      self.min_ms,
            "max_ms":      self.max_ms,
            "median_ms":   self.median_ms,
            "p95_ms":      self.p95_ms,
            "p99_ms":      self.p99_ms,
            "error_rate":  self.error_rate,
            "rps":         self.rps,
            "is_slow":     self.is_slow,
            "timestamp":   self.timestamp,
        }


# ─── APIOptimizer ─────────────────────────────────────────────────────────────

class APIOptimizer:
    """
    Accumulates request metrics per endpoint and provides ranked analysis.

    Thread-safe; keeps last 1 000 timing samples per endpoint.
    """

    _MAX_SAMPLES = 1_000
    _SLOW_THRESHOLD_MS = 500.0

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # {(path, method): deque of (elapsed_ms, is_error, timestamp)}
        self._data: Dict[Tuple[str, str], Deque[Tuple[float, bool, str]]] = {}
        self._request_times: Dict[Tuple[str, str], Deque[float]] = {}

    def record(
        self,
        *,
        path: str,
        method: str,
        elapsed_ms: float,
        status_code: int,
    ) -> None:
        """Record one completed HTTP request."""
        is_error = status_code >= 400
        key = (path, method.upper())
        ts = _now_iso()

        with self._lock:
            if key not in self._data:
                self._data[key] = deque(maxlen=self._MAX_SAMPLES)
                self._request_times[key] = deque(maxlen=self._MAX_SAMPLES)
            self._data[key].append((elapsed_ms, is_error, ts))
            self._request_times[key].append(elapsed_ms)

        if elapsed_ms > self._SLOW_THRESHOLD_MS:
            logger.warning(
                f"[APIOptimizer] Slow request: {method} {path} "
                f"took {elapsed_ms:.0f}ms (threshold: {self._SLOW_THRESHOLD_MS}ms)"
            )

    def get_endpoint_stats(self, path: str, method: str = "GET") -> Optional[EndpointStats]:
        """Return stats for one specific endpoint."""
        key = (path, method.upper())
        with self._lock:
            samples = list(self._data.get(key, []))
        if not samples:
            return None
        return self._compute_stats(path, method.upper(), samples)

    def _compute_stats(
        self, path: str, method: str, samples: List[Tuple[float, bool, str]]
    ) -> EndpointStats:
        timings = [s[0] for s in samples]
        errors = sum(1 for s in samples if s[1])
        n = len(timings)
        sorted_t = sorted(timings)

        # RPS over the last 60 seconds
        import time as _time
        now_ts = _time.time()
        recent = [s for s in samples if _iso_to_epoch(s[2]) >= now_ts - 60.0]
        rps = round(len(recent) / 60.0, 2)

        return EndpointStats(
            path=path,
            method=method,
            total_calls=n,
            errors=errors,
            avg_ms=round(statistics.mean(timings), 2),
            min_ms=round(sorted_t[0], 2),
            max_ms=round(sorted_t[-1], 2),
            median_ms=round(statistics.median(timings), 2),
            p95_ms=round(sorted_t[int(n * 0.95)], 2) if n >= 20 else round(sorted_t[-1], 2),
            p99_ms=round(sorted_t[int(n * 0.99)], 2) if n >= 100 else round(sorted_t[-1], 2),
            error_rate=round(errors / n, 4),
            rps=rps,
        )

    def get_all_stats(self) -> List[EndpointStats]:
        with self._lock:
            keys = list(self._data.keys())
        stats = []
        for path, method in keys:
            with self._lock:
                samples = list(self._data.get((path, method), []))
            if samples:
                stats.append(self._compute_stats(path, method, samples))
        return stats

    def get_slow_endpoints(self, threshold_ms: float = 500.0) -> List[EndpointStats]:
        return [s for s in self.get_all_stats() if s.p95_ms > threshold_ms]

    def get_ranked_by_latency(self, top_n: int = 10) -> List[EndpointStats]:
        """Return endpoints sorted by avg_ms descending."""
        return sorted(self.get_all_stats(), key=lambda s: s.avg_ms, reverse=True)[:top_n]

    def get_ranked_by_error_rate(self, top_n: int = 10) -> List[EndpointStats]:
        return sorted(self.get_all_stats(), key=lambda s: s.error_rate, reverse=True)[:top_n]

    def get_api_report(self) -> Dict[str, Any]:
        """Full API performance report."""
        all_stats = self.get_all_stats()
        slow = self.get_slow_endpoints()
        ranked = self.get_ranked_by_latency()

        return {
            "timestamp": _now_iso(),
            "total_endpoints_tracked": len(all_stats),
            "slow_endpoints": [s.to_dict() for s in slow],
            "ranked_by_latency": [s.to_dict() for s in ranked],
            "all_endpoints": [s.to_dict() for s in all_stats],
        }

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._request_times.clear()

    def reset(self) -> None:
        """Alias for clear() — wipe all accumulated endpoint metrics."""
        self.clear()


def _iso_to_epoch(ts: str) -> float:
    """Convert ISO-8601 string to Unix epoch float."""
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0


# ── Singleton ─────────────────────────────────────────────────────────────────
_api_optimizer = APIOptimizer()


def get_api_optimizer() -> APIOptimizer:
    return _api_optimizer


def record_request(
    path: str,
    method: str,
    elapsed_ms: float,
    status_code: int,
) -> None:
    """Module-level convenience: record one request into the global optimizer."""
    _api_optimizer.record(
        path=path, method=method,
        elapsed_ms=elapsed_ms, status_code=status_code,
    )


def get_api_stats() -> Dict[str, Any]:
    """Return the full API performance report."""
    return _api_optimizer.get_api_report()

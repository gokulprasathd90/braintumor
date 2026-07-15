"""
app/performance/cache.py — Cache optimization and analytics.

Provides:
  - CacheOptimizer: wraps ModelCache with tuning recommendations
  - CacheStats: snapshot of hit/miss/eviction metrics
  - PredictionCache: thin LRU cache for repeated identical predictions
  - DatasetMetadataCache: caches dataset_info.json reads
  - DashboardCache: time-bounded cache for dashboard snapshots
  - get_cache_report: composite report across all caches

Usage
-----
    from app.performance.cache import get_cache_optimizer, get_cache_report

    optimizer = get_cache_optimizer()
    report    = optimizer.get_report()
    full      = get_cache_report()
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logging import logger


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── CacheStats dataclass ─────────────────────────────────────────────────────

@dataclass
class CacheStats:
    """Snapshot of cache performance metrics."""
    name:         str
    capacity:     int
    size:         int
    hit_rate:     float
    total_hits:   int
    total_misses: int
    total_evictions: int
    avg_load_ms:  Optional[float]
    timestamp:    str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":            self.name,
            "capacity":        self.capacity,
            "size":            self.size,
            "utilization":     round(self.size / max(self.capacity, 1), 3),
            "hit_rate":        self.hit_rate,
            "total_hits":      self.total_hits,
            "total_misses":    self.total_misses,
            "total_evictions": self.total_evictions,
            "avg_load_ms":     self.avg_load_ms,
            "timestamp":       self.timestamp,
        }


# ─── CacheOptimizer ───────────────────────────────────────────────────────────

class CacheOptimizer:
    """
    Analyses ModelCache performance and provides tuning recommendations.

    Wraps the process-wide ``_cache`` singleton and records eviction counts,
    load durations, and access patterns.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._evictions = 0
        self._load_times: List[float] = []

    def get_model_cache_stats(self) -> CacheStats:
        """Return CacheStats snapshot from the live ModelCache."""
        from app.inference.cache import _cache
        s = _cache.stats()
        avg_load: Optional[float] = None
        if s.get("entries"):
            load_times = [e.get("load_duration_ms", 0) for e in s["entries"]]
            avg_load = round(sum(load_times) / len(load_times), 2) if load_times else None

        total = s["total_hits"] + s["total_misses"]
        return CacheStats(
            name="model_cache",
            capacity=s["capacity"],
            size=s["size"],
            hit_rate=s["hit_rate"],
            total_hits=s["total_hits"],
            total_misses=s["total_misses"],
            total_evictions=self._evictions,
            avg_load_ms=avg_load,
        )

    def recommend(self) -> List[str]:
        """Return tuning recommendations based on current cache state."""
        from app.inference.cache import _cache
        s = _cache.stats()
        recs: List[str] = []
        hit_rate = s["hit_rate"]
        size = s["size"]
        cap = s["capacity"]

        if hit_rate < 0.5 and (s["total_hits"] + s["total_misses"]) > 20:
            recs.append(
                f"Hit rate is low ({hit_rate:.0%}). "
                "Consider pre-warming the most-used models at startup."
            )
        if size >= cap and cap < 4:
            recs.append(
                f"Cache is full (size={size}/{cap}). "
                "Consider increasing ModelCache capacity."
            )
        if size == 0:
            recs.append(
                "No models are cached. Pre-load the active model "
                "during application startup to reduce first-request latency."
            )
        if hit_rate >= 0.9:
            recs.append(f"Cache performing well (hit_rate={hit_rate:.0%}).")
        return recs or ["Cache configuration looks healthy."]

    def benchmark_cache_warmup(self, model_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Measure time to warm up the cache with specified models."""
        from app.inference.cache import _cache
        from app.models.load_model import is_model_available
        model_names = model_names or ["efficientnet", "resnet50", "vgg16", "cnn"]
        results: List[Dict[str, Any]] = []

        for name in model_names:
            if not is_model_available(name):
                results.append({"model": name, "status": "skipped",
                                 "reason": "no saved weights"})
                continue
            if _cache.is_cached(name):
                results.append({"model": name, "status": "already_cached",
                                 "load_ms": 0.0})
                continue
            t0 = time.perf_counter()
            try:
                _cache.load(name)
                ms = round((time.perf_counter() - t0) * 1000, 1)
                results.append({"model": name, "status": "loaded", "load_ms": ms})
            except Exception as exc:
                results.append({"model": name, "status": "error",
                                 "error": str(exc)})
        return {"warmup_results": results}

    def get_report(self) -> Dict[str, Any]:
        """Full cache optimization report."""
        stats = self.get_model_cache_stats()
        return {
            "timestamp": _now_iso(),
            "model_cache": stats.to_dict(),
            "prediction_cache": _prediction_cache.get_stats(),
            "dataset_metadata_cache": _dataset_cache.get_stats(),
            "dashboard_cache": _dashboard_cache.get_stats(),
            "recommendations": self.recommend(),
        }


# ─── PredictionCache — deduplicate identical prediction requests ──────────────

class _PredictionCache:
    """
    LRU cache for repeated identical image+model predictions.

    Key: SHA-256 of (image_bytes + model_name).
    TTL: entries expire after ``ttl_s`` seconds.
    """

    def __init__(self, capacity: int = 256, ttl_s: float = 300.0) -> None:
        self._cap = capacity
        self._ttl = ttl_s
        self._lock = threading.RLock()
        self._store: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _key(self, image_bytes: bytes, model_name: str) -> str:
        h = hashlib.sha256(image_bytes + model_name.encode()).hexdigest()
        return h[:32]

    def get(self, image_bytes: bytes, model_name: str) -> Optional[Any]:
        key = self._key(image_bytes, model_name)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def set(self, image_bytes: bytes, model_name: str, value: Any) -> None:
        key = self._key(image_bytes, model_name)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            else:
                if len(self._store) >= self._cap:
                    self._store.popitem(last=False)
            self._store[key] = (value, time.time() + self._ttl)

    def invalidate(self, model_name: Optional[str] = None) -> int:
        """Remove all cached predictions for *model_name* (or all if None)."""
        with self._lock:
            if model_name is None:
                count = len(self._store)
                self._store.clear()
                return count
            # Can't filter by model_name from key alone — clear all
            count = len(self._store)
            self._store.clear()
            return count

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "name": "prediction_cache",
                "capacity": self._cap,
                "size": len(self._store),
                "ttl_s": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            }


# ─── DatasetMetadataCache ─────────────────────────────────────────────────────

class _DatasetMetadataCache:
    """Caches dataset_info.json reads in memory with TTL."""

    def __init__(self, ttl_s: float = 60.0) -> None:
        self._ttl = ttl_s
        self._lock = threading.RLock()
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, path: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(path)
            if entry is None:
                self._misses += 1
                return None
            value, expires = entry
            if time.time() > expires:
                del self._store[path]
                self._misses += 1
                return None
            self._hits += 1
            return value

    def set(self, path: str, value: Any) -> None:
        with self._lock:
            self._store[path] = (value, time.time() + self._ttl)

    def invalidate(self, path: Optional[str] = None) -> None:
        with self._lock:
            if path is None:
                self._store.clear()
            else:
                self._store.pop(path, None)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "name": "dataset_metadata_cache",
                "size": len(self._store),
                "ttl_s": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            }


# ─── DashboardCache ───────────────────────────────────────────────────────────

class _DashboardCache:
    """TTL-based cache for dashboard metric snapshots."""

    def __init__(self, ttl_s: float = 5.0) -> None:
        self._ttl = ttl_s
        self._lock = threading.RLock()
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            value, expires = entry
            if time.time() > expires:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (value, time.time() + self._ttl)

    def invalidate(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "name": "dashboard_cache",
                "size": len(self._store),
                "ttl_s": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            }


# ── Singletons ────────────────────────────────────────────────────────────────
_prediction_cache    = _PredictionCache(capacity=256, ttl_s=300.0)
_dataset_cache       = _DatasetMetadataCache(ttl_s=60.0)
_dashboard_cache     = _DashboardCache(ttl_s=5.0)
_cache_optimizer     = CacheOptimizer()


def get_cache_optimizer() -> CacheOptimizer:
    return _cache_optimizer


def get_prediction_cache() -> _PredictionCache:
    return _prediction_cache


def get_dataset_cache() -> _DatasetMetadataCache:
    return _dataset_cache


def get_dashboard_cache() -> _DashboardCache:
    return _dashboard_cache


def get_cache_report() -> Dict[str, Any]:
    """Return a composite cache report for all caches."""
    return _cache_optimizer.get_report()

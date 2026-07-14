"""
app/metrics/inference.py — In-process inference metrics accumulator.

Records every prediction (single and batch) and exposes aggregated
statistics:

  - Total predictions / batches
  - Per-model prediction counts
  - Success / failure rates
  - Average, min, max inference latency
  - Confidence distribution (histogram buckets)
  - Top predicted classes
  - Recent prediction history (rolling window)

Usage
-----
    from app.metrics.inference import record_prediction, get_inference_metrics

    record_prediction(result)        # after each single inference
    record_batch_prediction(result)  # after each batch run

    stats = get_inference_metrics()
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Confidence histogram bucket edges ────────────────────────────────────────
_CONF_BUCKETS = [0.0, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0]
_BUCKET_LABELS = ["<50%", "50–70%", "70–80%", "80–90%", "90–95%", "95–100%"]


def _bucket_index(confidence: float) -> int:
    for i in range(len(_CONF_BUCKETS) - 1):
        if _CONF_BUCKETS[i] <= confidence < _CONF_BUCKETS[i + 1]:
            return i
    return len(_BUCKET_LABELS) - 1  # catch 1.0


class InferenceMetricsStore:
    """
    Thread-safe in-process accumulator for inference statistics.

    Attributes
    ----------
    _lock : threading.RLock
    _total : int                    Total single predictions
    _succeeded : int                Successful single predictions
    _failed : int                   Failed single predictions
    _per_model : dict               Counts per architecture name
    _timing_ms : list[float]        Latency samples (last _MAX_SAMPLES)
    _confidence_hist : list[int]    Histogram bin counts
    _class_counts : dict            Prediction counts per class
    _batch_total : int              Total batch runs
    _batch_images : int             Total images across all batch runs
    _recent : deque                 Rolling recent predictions (last 100)
    """

    _MAX_SAMPLES = 1_000   # keep last N timing samples
    _MAX_RECENT  = 100     # keep last N individual prediction records

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reset()

    def _reset(self) -> None:
        self._total = 0
        self._succeeded = 0
        self._failed = 0
        self._per_model: Dict[str, int] = {}
        self._timing_ms: List[float] = []
        self._confidence_hist: List[int] = [0] * len(_BUCKET_LABELS)
        self._class_counts: Dict[str, int] = {}
        self._batch_total = 0
        self._batch_images = 0
        self._batch_succeeded = 0
        self._batch_failed = 0
        self._recent: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_RECENT)
        self._started_at: str = _now_iso()

    def reset(self) -> None:
        with self._lock:
            self._reset()

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(
        self,
        *,
        model_name: str,
        predicted_class: str,
        confidence: float,
        timing_ms: float,
        success: bool,
        image_id: Optional[str] = None,
    ) -> None:
        """Record one single-image prediction outcome."""
        with self._lock:
            self._total += 1
            if success:
                self._succeeded += 1
                # Per-model
                self._per_model[model_name] = self._per_model.get(model_name, 0) + 1
                # Timing
                self._timing_ms.append(timing_ms)
                if len(self._timing_ms) > self._MAX_SAMPLES:
                    self._timing_ms = self._timing_ms[-self._MAX_SAMPLES:]
                # Confidence histogram
                bi = _bucket_index(confidence)
                self._confidence_hist[bi] += 1
                # Class counts
                self._class_counts[predicted_class] = (
                    self._class_counts.get(predicted_class, 0) + 1
                )
            else:
                self._failed += 1

            # Recent predictions log
            self._recent.append({
                "image_id": image_id,
                "model_name": model_name,
                "predicted_class": predicted_class if success else None,
                "confidence": confidence if success else None,
                "timing_ms": timing_ms,
                "success": success,
                "timestamp": _now_iso(),
            })

    def record_batch(
        self,
        *,
        model_name: str,
        total: int,
        succeeded: int,
        failed: int,
        timing_ms: float,
        class_distribution: Dict[str, int],
    ) -> None:
        """Record one batch prediction run."""
        with self._lock:
            self._batch_total += 1
            self._batch_images += total
            self._batch_succeeded += succeeded
            self._batch_failed += failed
            # Merge class distribution into overall counts
            for cls, count in class_distribution.items():
                self._class_counts[cls] = self._class_counts.get(cls, 0) + count
            # Count model usage for batch
            if succeeded > 0:
                self._per_model[model_name] = (
                    self._per_model.get(model_name, 0) + succeeded
                )

    # ── Aggregation ───────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable snapshot of all inference metrics."""
        with self._lock:
            timing = self._timing_ms
            total_t = self._total

            if timing:
                avg_ms = round(sum(timing) / len(timing), 2)
                min_ms = round(min(timing), 2)
                max_ms = round(max(timing), 2)
                p95_ms = round(sorted(timing)[int(len(timing) * 0.95)], 2) if len(timing) >= 20 else None
            else:
                avg_ms = min_ms = max_ms = p95_ms = None

            success_rate = (
                round(self._succeeded / total_t, 4) if total_t > 0 else 0.0
            )

            top_classes = sorted(
                self._class_counts.items(), key=lambda x: x[1], reverse=True
            )

            return {
                "timestamp": _now_iso(),
                "started_at": self._started_at,
                "total_predictions": total_t,
                "succeeded": self._succeeded,
                "failed": self._failed,
                "success_rate": success_rate,
                "per_model_counts": dict(self._per_model),
                "avg_latency_ms": avg_ms,
                "min_latency_ms": min_ms,
                "max_latency_ms": max_ms,
                "p95_latency_ms": p95_ms,
                "confidence_distribution": {
                    "buckets": _BUCKET_LABELS,
                    "counts": list(self._confidence_hist),
                },
                "class_distribution": dict(self._class_counts),
                "top_classes": [
                    {"class_name": cls, "count": cnt}
                    for cls, cnt in top_classes[:10]
                ],
                "batch_runs": self._batch_total,
                "batch_images_processed": self._batch_images,
                "batch_succeeded": self._batch_succeeded,
                "batch_failed": self._batch_failed,
                "recent_predictions": list(self._recent),
            }


# ── Module-level singleton ────────────────────────────────────────────────────

_inference_store = InferenceMetricsStore()


def get_inference_store() -> InferenceMetricsStore:
    """Return the process-wide singleton InferenceMetricsStore."""
    return _inference_store


def record_prediction(result: Any) -> None:
    """
    Record a single PredictionResult (dataclass or dict) into the store.

    Accepts both the PredictionResult dataclass and its to_dict() form.
    """
    store = _inference_store
    try:
        if hasattr(result, "predicted_class"):
            # dataclass form
            store.record(
                model_name=result.metadata.model_name,
                predicted_class=result.predicted_class,
                confidence=result.confidence,
                timing_ms=result.timing_ms,
                success=result.error is None,
                image_id=result.image_id,
            )
        elif isinstance(result, dict):
            meta = result.get("metadata", {})
            store.record(
                model_name=meta.get("model_name", "unknown"),
                predicted_class=result.get("predicted_class", "unknown"),
                confidence=result.get("confidence", 0.0),
                timing_ms=result.get("timing_ms", 0.0),
                success=result.get("error") is None,
                image_id=result.get("image_id"),
            )
    except Exception:
        pass  # metrics are non-fatal


def record_batch_prediction(result: Any) -> None:
    """
    Record a BatchPredictionResult (dataclass or dict) into the store.
    """
    store = _inference_store
    try:
        if hasattr(result, "succeeded"):
            store.record_batch(
                model_name=result.model_name,
                total=result.total,
                succeeded=result.succeeded,
                failed=result.failed,
                timing_ms=result.timing_ms,
                class_distribution=result.class_distribution,
            )
        elif isinstance(result, dict):
            store.record_batch(
                model_name=result.get("model_name", "unknown"),
                total=result.get("total", 0),
                succeeded=result.get("succeeded", 0),
                failed=result.get("failed", 0),
                timing_ms=result.get("timing_ms", 0.0),
                class_distribution=result.get("class_distribution", {}),
            )
    except Exception:
        pass  # metrics are non-fatal


def get_inference_metrics() -> Dict[str, Any]:
    """Return a dict snapshot of all inference metrics."""
    return _inference_store.to_dict()

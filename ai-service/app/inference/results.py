"""
app/inference/results.py — Typed result models for inference output.

Provides four immutable dataclasses used throughout the inference pipeline:

  PredictionMetadata    — contextual information about the model and image
  TopKPrediction        — one entry in the top-K list
  PredictionResult      — complete single-image prediction output
  BatchPredictionResult — aggregated result from batch / ZIP inference

All dataclasses are JSON-serialisable via ``to_dict()`` and reconstructable
via ``from_dict()``.

Usage
-----
    from app.inference.results import PredictionResult

    result = PredictionResult(
        image_id="abc-123",
        predicted_class="glioma",
        confidence=0.9732,
        probabilities={"glioma": 0.9732, "meningioma": 0.0153, ...},
        top_k=[...],
        metadata=PredictionMetadata(...),
        timing_ms=42.1,
    )
    d = result.to_dict()
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── PredictionMetadata ───────────────────────────────────────────────────────

@dataclass
class PredictionMetadata:
    """
    Contextual information attached to every prediction.

    Attributes
    ----------
    model_name : str
        Architecture key used for inference.
    model_version : str | None
        Version tag read from model_info.json (None if unavailable).
    image_size : int
        Spatial resolution used by the model (H = W).
    class_names : list[str]
        Ordered class labels.
    predicted_at : str
        ISO-8601 UTC timestamp of prediction.
    source_path : str | None
        Original file path (batch inference only; None for uploaded bytes).
    gradcam_path : str | None
        Absolute path to the saved Grad-CAM overlay PNG, or None.
    """

    model_name:    str
    class_names:   List[str]
    image_size:    int
    model_version: Optional[str] = None
    predicted_at:  str           = field(default_factory=_now_iso)
    source_path:   Optional[str] = None
    gradcam_path:  Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PredictionMetadata":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


# ─── TopKPrediction ───────────────────────────────────────────────────────────

@dataclass
class TopKPrediction:
    """One entry in the top-K prediction list."""

    rank:        int    # 1-indexed
    class_name:  str
    class_index: int
    probability: float  # 4 d.p.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─── PredictionResult ─────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    """
    Complete prediction output for a single image.

    Attributes
    ----------
    image_id : str
        UUID or caller-supplied identifier for this prediction.
    predicted_class : str
        Top-1 predicted class label.
    predicted_class_index : int
        Index of the top-1 class in ``class_names``.
    confidence : float
        Top-1 probability (0–1, 4 d.p.).
    is_high_confidence : bool
        True when confidence ≥ InferenceConfig.confidence_threshold.
    probabilities : dict[str, float]
        Full probability distribution over all classes.
    top_k : list[TopKPrediction]
        Ordered list of the K highest-probability predictions.
    timing_ms : float
        Wall-clock inference time in milliseconds.
    metadata : PredictionMetadata
        Model and image provenance information.
    error : str | None
        Non-None when the prediction failed (batch scenarios).
    """

    image_id:              str
    predicted_class:       str
    predicted_class_index: int
    confidence:            float
    is_high_confidence:    bool
    probabilities:         Dict[str, float]
    top_k:                 List[TopKPrediction]
    timing_ms:             float
    metadata:              PredictionMetadata
    error:                 Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Flatten nested metadata
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PredictionResult":
        meta_raw = d.pop("metadata", {})
        top_k_raw = d.pop("top_k", [])
        meta = PredictionMetadata.from_dict(meta_raw) if meta_raw else PredictionMetadata(
            model_name="unknown", class_names=[], image_size=224
        )
        top_k = [TopKPrediction(**t) for t in top_k_raw]
        return cls(metadata=meta, top_k=top_k, **d)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ─── BatchItemResult ──────────────────────────────────────────────────────────

@dataclass
class BatchItemResult:
    """
    One image's outcome within a batch run.

    Wraps PredictionResult on success, or records filename + error on failure.
    """

    filename:    str
    success:     bool
    result:      Optional[PredictionResult] = None
    error:       Optional[str]              = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "success":  self.success,
            "result":   self.result.to_dict() if self.result else None,
            "error":    self.error,
        }


# ─── BatchPredictionResult ────────────────────────────────────────────────────

@dataclass
class BatchPredictionResult:
    """
    Aggregated output from a batch or ZIP inference run.

    Attributes
    ----------
    total : int
        Total number of images processed (success + failure).
    succeeded : int
        Images that produced a valid prediction.
    failed : int
        Images that raised an error.
    results : list[BatchItemResult]
        Per-image results (ordered as submitted).
    timing_ms : float
        Total wall-clock time for the batch in milliseconds.
    model_name : str
        Architecture used.
    source_type : str
        "directory" | "zip" | "list"
    export_paths : dict
        Paths to any exported files (csv_path, json_path).
    """

    total:        int
    succeeded:    int
    failed:       int
    results:      List[BatchItemResult]
    timing_ms:    float
    model_name:   str
    source_type:  str
    export_paths: Dict[str, str] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.succeeded / self.total, 4)

    @property
    def class_distribution(self) -> Dict[str, int]:
        """Count of each predicted class among successful predictions."""
        counts: Dict[str, int] = {}
        for item in self.results:
            if item.success and item.result:
                cls = item.result.predicted_class
                counts[cls] = counts.get(cls, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total":              self.total,
            "succeeded":          self.succeeded,
            "failed":             self.failed,
            "success_rate":       self.success_rate,
            "timing_ms":          round(self.timing_ms, 2),
            "model_name":         self.model_name,
            "source_type":        self.source_type,
            "class_distribution": self.class_distribution,
            "export_paths":       self.export_paths,
            "results":            [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary_dict(self) -> Dict[str, Any]:
        """Lightweight summary without per-image results (for API responses)."""
        return {
            "total":              self.total,
            "succeeded":          self.succeeded,
            "failed":             self.failed,
            "success_rate":       self.success_rate,
            "timing_ms":          round(self.timing_ms, 2),
            "model_name":         self.model_name,
            "source_type":        self.source_type,
            "class_distribution": self.class_distribution,
            "export_paths":       self.export_paths,
        }

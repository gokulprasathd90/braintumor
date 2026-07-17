"""
app/metrics — Metrics & Monitoring package.

Public API
----------
    from app.metrics import (
        get_system_metrics,
        get_inference_metrics,
        get_training_metrics,
        get_dashboard_overview,
        record_prediction,
        metrics_store,
    )
"""

from app.metrics.system import get_system_metrics
from app.metrics.inference import (
    get_inference_metrics,
    record_prediction,
    record_batch_prediction,
    get_inference_store,
)
from app.metrics.training import get_training_metrics
from app.metrics.dashboard import get_dashboard_overview
from app.metrics.storage import MetricsStorage, get_metrics_store

# Module-level singleton — shared across all requests
metrics_store = get_metrics_store()

__all__ = [
    "get_system_metrics",
    "get_inference_metrics",
    "get_training_metrics",
    "get_dashboard_overview",
    "record_prediction",
    "record_batch_prediction",
    "get_inference_store",
    "metrics_store",
    "MetricsStorage",
    "get_metrics_store",
]

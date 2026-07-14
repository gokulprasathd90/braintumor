"""
app/metrics/dashboard.py — Composite dashboard overview aggregator.

Combines system, inference, and training metrics into a single overview
payload that drives the frontend monitoring dashboard.

Usage
-----
    from app.metrics.dashboard import get_dashboard_overview

    overview = get_dashboard_overview()
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.metrics.system import get_system_metrics
from app.metrics.inference import get_inference_metrics
from app.metrics.training import get_training_metrics


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model_cache_stats() -> Dict[str, Any]:
    """Pull model cache statistics from the inference cache layer."""
    try:
        from app.inference.cache import get_cache_stats
        return get_cache_stats()
    except Exception:
        return {}


def _service_version() -> str:
    try:
        from app.core.config import settings  # noqa: F401
        return "1.0.0"
    except Exception:
        return "unknown"


def get_dashboard_overview() -> Dict[str, Any]:
    """
    Return a composite overview payload combining all metric domains.

    Returns
    -------
    dict with keys:
        timestamp, service_version,
        system   — CPU / RAM / disk snapshot (key fields only),
        inference — aggregated prediction statistics,
        training  — job counts and best accuracy,
        models    — cache stats,
        alerts    — list of triggered threshold alerts
    """
    sys_m  = get_system_metrics()
    inf_m  = get_inference_metrics()
    trn_m  = get_training_metrics()
    cache  = _model_cache_stats()
    alerts = _compute_alerts(sys_m, inf_m)

    return {
        "timestamp": _now_iso(),
        "service_version": _service_version(),
        "system": {
            "cpu_percent": sys_m.get("cpu_percent"),
            "ram_percent": sys_m.get("ram_percent"),
            "ram_used_mb": sys_m.get("ram_used_mb"),
            "disk_percent": sys_m.get("disk_percent"),
            "gpu_available": sys_m.get("gpu_available", False),
            "uptime_seconds": sys_m.get("uptime_seconds"),
            "platform": sys_m.get("platform"),
        },
        "inference": {
            "total_predictions": inf_m.get("total_predictions", 0),
            "succeeded": inf_m.get("succeeded", 0),
            "failed": inf_m.get("failed", 0),
            "success_rate": inf_m.get("success_rate", 0.0),
            "avg_latency_ms": inf_m.get("avg_latency_ms"),
            "p95_latency_ms": inf_m.get("p95_latency_ms"),
            "top_classes": inf_m.get("top_classes", [])[:5],
            "batch_runs": inf_m.get("batch_runs", 0),
        },
        "training": {
            "total_jobs": trn_m.get("total_jobs", 0),
            "running_jobs": trn_m.get("running_jobs", 0),
            "completed_jobs": trn_m.get("completed_jobs", 0),
            "failed_jobs": trn_m.get("failed_jobs", 0),
            "best_val_accuracy": trn_m.get("best_val_accuracy"),
            "total_experiments": trn_m.get("total_experiments", 0),
        },
        "models": cache,
        "alerts": alerts,
    }


def _compute_alerts(
    sys_m: Dict[str, Any],
    inf_m: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate threshold-based alert objects.

    Each alert has: level ("warning" | "critical"), domain, message.
    """
    alerts: List[Dict[str, Any]] = []

    cpu = sys_m.get("cpu_percent")
    if cpu is not None:
        if cpu >= 95:
            alerts.append({"level": "critical", "domain": "system", "message": f"CPU usage critical: {cpu}%"})
        elif cpu >= 80:
            alerts.append({"level": "warning", "domain": "system", "message": f"CPU usage high: {cpu}%"})

    ram = sys_m.get("ram_percent")
    if ram is not None:
        if ram >= 95:
            alerts.append({"level": "critical", "domain": "system", "message": f"RAM usage critical: {ram}%"})
        elif ram >= 85:
            alerts.append({"level": "warning", "domain": "system", "message": f"RAM usage high: {ram}%"})

    disk = sys_m.get("disk_percent")
    if disk is not None:
        if disk >= 95:
            alerts.append({"level": "critical", "domain": "system", "message": f"Disk usage critical: {disk}%"})
        elif disk >= 85:
            alerts.append({"level": "warning", "domain": "system", "message": f"Disk usage high: {disk}%"})

    success_rate = inf_m.get("success_rate", 1.0)
    total = inf_m.get("total_predictions", 0)
    if total >= 10 and success_rate < 0.8:
        alerts.append({
            "level": "warning",
            "domain": "inference",
            "message": f"Prediction success rate low: {success_rate:.1%}",
        })

    avg_lat = inf_m.get("avg_latency_ms")
    if avg_lat is not None and avg_lat > 2000:
        alerts.append({
            "level": "warning",
            "domain": "inference",
            "message": f"Average inference latency high: {avg_lat:.0f}ms",
        })

    return alerts


def get_history_summary(
    metric_type: str = "system",
    hours: int = 24,
) -> Dict[str, Any]:
    """
    Return rolling history for the requested metric type.

    Parameters
    ----------
    metric_type : str
        "system" | "inference" | "training" | "overview"
    hours : int
        How many hours of history to return (max 168 = 7 days).
    """
    hours = min(hours, 168)
    from app.metrics.storage import get_metrics_store
    store = get_metrics_store()
    history = store.load_history(metric_type=metric_type, hours=hours)
    return {
        "metric_type": metric_type,
        "hours": hours,
        "count": len(history),
        "data": history,
    }

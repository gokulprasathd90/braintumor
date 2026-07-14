"""
app/metrics/training.py — Training job metrics aggregator.

Reads live state from the TrainingJobStore and the experiment log
directory to produce a summary of all training activity.

Usage
-----
    from app.metrics.training import get_training_metrics

    metrics = get_training_metrics()
    print(metrics["total_jobs"], metrics["running_jobs"])
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_seconds(started: Optional[str], finished: Optional[str]) -> Optional[float]:
    """Return the duration in seconds between two ISO-8601 timestamps."""
    if started is None:
        return None
    try:
        t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
        t1 = (
            datetime.fromisoformat(finished.replace("Z", "+00:00"))
            if finished
            else datetime.now(timezone.utc)
        )
        return round((t1 - t0).total_seconds(), 1)
    except Exception:
        return None


def _load_experiments() -> List[Dict[str, Any]]:
    """Load all experiment records from the experiment log directory."""
    experiments: List[Dict[str, Any]] = []
    try:
        from app.core.config import settings
        log_dir = settings.log_dir / "experiments"
        if not log_dir.exists():
            return experiments
        import json
        for p in sorted(log_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    experiments.append(json.load(fh))
            except Exception:
                continue
    except Exception:
        pass
    return experiments


def get_training_metrics() -> Dict[str, Any]:
    """
    Aggregate training metrics from the job store and experiment logs.

    Returns
    -------
    dict with keys:
        timestamp,
        total_jobs, running_jobs, queued_jobs, completed_jobs, failed_jobs,
        total_experiments, best_val_accuracy, avg_duration_s,
        architecture_counts, recent_jobs, recent_experiments
    """
    from app.training.job_store import get_job_store

    store = get_job_store()
    all_jobs = store.list_jobs(limit=200)

    # ── Job status counts ─────────────────────────────────────────────────────
    status_counts: Dict[str, int] = {
        "queued": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
    }
    for job in all_jobs:
        s = job.get("status", "unknown")
        if s in status_counts:
            status_counts[s] += 1

    # ── Architecture popularity from job configs ───────────────────────────────
    arch_counts: Dict[str, int] = {}
    for job in all_jobs:
        cfg = job.get("config") or {}
        arch = cfg.get("architecture") or cfg.get("model_name") or "unknown"
        arch_counts[arch] = arch_counts.get(arch, 0) + 1

    # ── Per-job duration ──────────────────────────────────────────────────────
    durations = []
    for job in all_jobs:
        if job.get("status") in ("completed", "failed"):
            d = _duration_seconds(job.get("started_at"), job.get("finished_at"))
            if d is not None:
                durations.append(d)

    avg_duration = round(sum(durations) / len(durations), 1) if durations else None

    # ── Recent jobs (last 10) ─────────────────────────────────────────────────
    recent_jobs = [
        {
            "job_id": j["job_id"],
            "status": j["status"],
            "architecture": (j.get("config") or {}).get("architecture", "unknown"),
            "created_at": j.get("created_at"),
            "started_at": j.get("started_at"),
            "finished_at": j.get("finished_at"),
            "duration_s": _duration_seconds(j.get("started_at"), j.get("finished_at")),
        }
        for j in all_jobs[:10]
    ]

    # ── Experiment data ───────────────────────────────────────────────────────
    experiments = _load_experiments()
    best_val_acc: Optional[float] = None
    for exp in experiments:
        val_acc = exp.get("best_val_accuracy")
        if val_acc is not None:
            if best_val_acc is None or val_acc > best_val_acc:
                best_val_acc = val_acc

    recent_experiments = [
        {
            "experiment_id": exp.get("experiment_id"),
            "architecture": exp.get("architecture"),
            "status": exp.get("status"),
            "best_val_accuracy": exp.get("best_val_accuracy"),
            "epochs_trained": exp.get("epochs_trained"),
            "duration_s": exp.get("duration_s"),
            "created_at": exp.get("created_at"),
        }
        for exp in experiments[:10]
    ]

    return {
        "timestamp": _now_iso(),
        "total_jobs": len(all_jobs),
        "queued_jobs": status_counts["queued"],
        "running_jobs": status_counts["running"],
        "completed_jobs": status_counts["completed"],
        "failed_jobs": status_counts["failed"],
        "avg_job_duration_s": avg_duration,
        "architecture_counts": arch_counts,
        "recent_jobs": recent_jobs,
        "total_experiments": len(experiments),
        "best_val_accuracy": best_val_acc,
        "recent_experiments": recent_experiments,
    }

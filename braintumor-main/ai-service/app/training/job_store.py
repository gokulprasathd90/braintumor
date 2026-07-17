"""
app/training/job_store.py — In-process async training job registry.

Provides ``TrainingJobStore``, a lightweight thread-safe store that tracks
background training jobs (started via the ``/api/v1/train/start`` endpoint).

Each job has:
  - A unique ``job_id`` (UUID4 hex string).
  - A ``status`` — "queued" | "running" | "completed" | "failed".
  - The ``experiment_id`` once the Trainer creates the Experiment record.
  - The final ``result`` dict once training finishes.
  - An ``error`` message if training fails.
  - Timestamps (``created_at``, ``started_at``, ``finished_at``).

This is an in-process store (dict-backed) suitable for single-worker
deployments.  For multi-worker / distributed setups replace with Redis or a
task queue such as Celery / RQ.

Usage
-----
    store = TrainingJobStore()
    job_id = store.create_job({"architecture": "resnet50", "epochs": 20})
    store.mark_running(job_id, experiment_id="resnet50-20240715-abc123")
    store.mark_completed(job_id, result={...})
    job = store.get(job_id)
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Valid status transitions
_STATUSES = ("queued", "running", "completed", "failed")


class TrainingJobStore:
    """
    Thread-safe in-process store for background training jobs.

    All public methods acquire a reentrant lock, so they are safe to call
    from multiple threads (e.g. a background thread running ``Trainer.run()``
    and a FastAPI request thread polling ``/status/{job_id}``).
    """

    def __init__(self) -> None:
        self._lock  = threading.RLock()
        self._store: Dict[str, Dict[str, Any]] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create_job(self, config_snapshot: Dict[str, Any]) -> str:
        """
        Register a new training job and return its ``job_id``.

        Parameters
        ----------
        config_snapshot : dict
            Serialised request body / TrainingConfig for logging purposes.

        Returns
        -------
        str
            UUID4 hex ``job_id``.
        """
        job_id = uuid.uuid4().hex
        with self._lock:
            self._store[job_id] = {
                "job_id":        job_id,
                "status":        "queued",
                "config":        config_snapshot,
                "experiment_id": None,
                "result":        None,
                "error":         None,
                "created_at":    _now_iso(),
                "started_at":    None,
                "finished_at":   None,
            }
        return job_id

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return the job record or ``None`` if not found."""
        with self._lock:
            job = self._store.get(job_id)
            return dict(job) if job else None

    def list_jobs(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Return a list of job records, newest-first.

        Parameters
        ----------
        status : str | None
            Filter by status (queued | running | completed | failed).
        limit : int
            Maximum entries to return.
        """
        with self._lock:
            jobs = list(self._store.values())

        if status:
            jobs = [j for j in jobs if j["status"] == status]

        jobs.sort(key=lambda j: j["created_at"], reverse=True)
        return jobs[:limit]

    # ── Status transitions ────────────────────────────────────────────────────

    def mark_running(self, job_id: str, *, experiment_id: str) -> None:
        """Transition job to 'running' and record the experiment_id."""
        with self._lock:
            job = self._store.get(job_id)
            if job is None:
                raise KeyError(f"Unknown job_id: {job_id}")
            job["status"] = "running"
            job["experiment_id"] = experiment_id
            job["started_at"] = _now_iso()

    def mark_completed(self, job_id: str, *, result: Dict[str, Any]) -> None:
        """Transition job to 'completed' and store the result dict."""
        with self._lock:
            job = self._store.get(job_id)
            if job is None:
                raise KeyError(f"Unknown job_id: {job_id}")
            job["status"] = "completed"
            job["result"] = result
            job["finished_at"] = _now_iso()

    def mark_failed(self, job_id: str, *, error: str) -> None:
        """Transition job to 'failed' and store the error message."""
        with self._lock:
            job = self._store.get(job_id)
            if job is None:
                raise KeyError(f"Unknown job_id: {job_id}")
            job["status"] = "failed"
            job["error"] = error
            job["finished_at"] = _now_iso()

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def delete(self, job_id: str) -> bool:
        """Remove a job from the store. Returns True if it existed."""
        with self._lock:
            return self._store.pop(job_id, None) is not None

    def clear_completed(self) -> int:
        """Remove all completed / failed jobs. Returns the count removed."""
        with self._lock:
            to_delete = [
                jid for jid, job in self._store.items()
                if job["status"] in ("completed", "failed")
            ]
            for jid in to_delete:
                del self._store[jid]
        return len(to_delete)

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


# ── Module-level singleton (shared across all FastAPI requests in the process) ─
_job_store = TrainingJobStore()


def get_job_store() -> TrainingJobStore:
    """Return the process-wide singleton ``TrainingJobStore``."""
    return _job_store

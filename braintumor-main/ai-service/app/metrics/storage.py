"""
app/metrics/storage.py — Persistent metrics storage with rolling history.

Persists metric snapshots to JSON files under logs/metrics/.
Maintains:
  - A rolling hourly history file (last 24 h)
  - A daily summary file per calendar day

Usage
-----
    from app.metrics.storage import get_metrics_store

    store = get_metrics_store()
    store.save_snapshot({"type": "system", ...})
    history = store.load_history(metric_type="system", hours=6)
    summary = store.load_daily_summary(date_str="2024-07-14")
"""

from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class MetricsStorage:
    """
    Persistent + in-memory metrics store.

    Snapshots are appended to a rolling JSON-Lines file keyed by metric
    type and calendar date.  An in-memory deque provides fast access to
    recent snapshots without I/O.

    Parameters
    ----------
    base_dir : Path
        Directory where metric files are written.
        Defaults to ``logs/metrics/`` relative to the config base dir.
    max_memory_snapshots : int
        Maximum snapshots to keep in memory per metric type.
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        max_memory_snapshots: int = 288,   # ~24 h at 5-min intervals
    ) -> None:
        if base_dir is None:
            try:
                from app.core.config import settings
                base_dir = settings.log_dir / "metrics"
            except Exception:
                base_dir = Path("logs") / "metrics"

        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._max = max_memory_snapshots
        self._lock = threading.RLock()
        # in-memory rolling buffers keyed by metric_type
        self._memory: Dict[str, Deque[Dict[str, Any]]] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def save_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """
        Persist a metrics snapshot and add it to the in-memory buffer.

        The snapshot must have a "type" key (e.g. "system", "inference",
        "training", "overview").  A "timestamp" key is added if absent.
        """
        if "timestamp" not in snapshot:
            snapshot = {**snapshot, "timestamp": _now_iso()}
        metric_type = snapshot.get("type", "general")

        with self._lock:
            # ── Memory buffer ─────────────────────────────────────────────────
            if metric_type not in self._memory:
                self._memory[metric_type] = deque(maxlen=self._max)
            self._memory[metric_type].append(snapshot)

            # ── Disk (JSON-Lines) ─────────────────────────────────────────────
            try:
                date_str = _today_str()
                file_path = self._base_dir / f"{metric_type}_{date_str}.jsonl"
                line = json.dumps(snapshot, ensure_ascii=False)
                with open(file_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except Exception:
                pass  # disk errors must not break metrics collection

    # ── Read ──────────────────────────────────────────────────────────────────

    def load_history(
        self,
        metric_type: str = "system",
        hours: int = 24,
        max_points: int = 288,
    ) -> List[Dict[str, Any]]:
        """
        Return up to ``max_points`` snapshots from the last ``hours`` hours.

        Tries the in-memory buffer first; falls back to disk if the buffer
        is cold (e.g. after a service restart).
        """
        with self._lock:
            buf = list(self._memory.get(metric_type, []))

        if buf:
            return buf[-max_points:]

        # Cold path: read from disk files
        cutoff_ts = _hours_ago_iso(hours)
        results: List[Dict[str, Any]] = []
        try:
            for p in sorted(self._base_dir.glob(f"{metric_type}_*.jsonl")):
                with open(p, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            snap = json.loads(line)
                            if snap.get("timestamp", "") >= cutoff_ts:
                                results.append(snap)
                        except Exception:
                            continue
        except Exception:
            pass

        results.sort(key=lambda s: s.get("timestamp", ""))
        return results[-max_points:]

    def load_daily_summary(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Return an aggregated daily summary for all metric types.

        Parameters
        ----------
        date_str : str | None
            "YYYY-MM-DD" format.  Defaults to today.
        """
        date_str = date_str or _today_str()
        summary: Dict[str, Any] = {"date": date_str, "types": {}}

        try:
            for p in self._base_dir.glob(f"*_{date_str}.jsonl"):
                mtype = p.stem.replace(f"_{date_str}", "")
                snapshots: List[Dict[str, Any]] = []
                with open(p, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            try:
                                snapshots.append(json.loads(line))
                            except Exception:
                                pass
                summary["types"][mtype] = {
                    "count": len(snapshots),
                    "first_ts": snapshots[0].get("timestamp") if snapshots else None,
                    "last_ts": snapshots[-1].get("timestamp") if snapshots else None,
                }
        except Exception:
            pass

        return summary

    def get_available_dates(self, metric_type: str = "system") -> List[str]:
        """Return sorted list of dates that have stored snapshots."""
        dates: List[str] = []
        try:
            for p in self._base_dir.glob(f"{metric_type}_*.jsonl"):
                date_part = p.stem.replace(f"{metric_type}_", "")
                if len(date_part) == 10:  # YYYY-MM-DD
                    dates.append(date_part)
        except Exception:
            pass
        return sorted(dates)

    def purge_old_files(self, keep_days: int = 30) -> int:
        """Delete snapshot files older than ``keep_days`` days."""
        removed = 0
        try:
            from datetime import timedelta
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=keep_days)
            ).strftime("%Y-%m-%d")
            for p in self._base_dir.glob("*.jsonl"):
                parts = p.stem.split("_")
                if parts:
                    date_part = parts[-1]
                    if len(date_part) == 10 and date_part < cutoff:
                        p.unlink(missing_ok=True)
                        removed += 1
        except Exception:
            pass
        return removed


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hours_ago_iso(hours: int) -> str:
    from datetime import timedelta
    return (
        datetime.now(timezone.utc) - timedelta(hours=hours)
    ).isoformat()


# ── Module-level singleton ────────────────────────────────────────────────────

_metrics_storage: Optional[MetricsStorage] = None
_storage_lock = threading.Lock()


def get_metrics_store() -> MetricsStorage:
    """Return the process-wide singleton MetricsStorage."""
    global _metrics_storage
    with _storage_lock:
        if _metrics_storage is None:
            _metrics_storage = MetricsStorage()
    return _metrics_storage

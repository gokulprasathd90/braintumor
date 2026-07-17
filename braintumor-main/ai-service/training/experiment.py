"""
training/experiment.py — Experiment tracking: dataclass, registry, persistence.

Every training run creates an ``Experiment`` record that captures:
  - a unique ID and wall-clock timestamps
  - the full TrainingConfig snapshot
  - dataset provenance (directory, split counts, class weights)
  - per-phase and final training history
  - post-training evaluation metrics
  - paths to the saved model and best checkpoint

All records are persisted as individual JSON files AND mirrored into a
single ``experiment_registry.json`` index for fast listing.

Directory layout
----------------
    <experiments_dir>/
        experiment_registry.json        ← index of all runs
        <experiment_id>/
            experiment.json             ← full metadata for one run
            training_config.json        ← serialised TrainingConfig

Default experiments_dir:  ``settings.log_dir / "experiments"``

Usage
-----
    from training.experiment import Experiment, ExperimentRegistry
    from training.config import TrainingConfig

    cfg = TrainingConfig(architecture="resnet50", epochs=20)
    exp = Experiment.create(cfg)
    exp.update_status("running")
    exp.record_phase_history(1, history_dict)
    exp.record_eval_metrics({"accuracy": 0.97, "f1": 0.96})
    exp.save()

    registry = ExperimentRegistry()
    all_runs  = registry.list_experiments()
    one_run   = registry.get(exp.experiment_id)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import logger
from training.config import TrainingConfig


# ─────────────────────────────────────────────────────────────────────────────
# Status values
# ─────────────────────────────────────────────────────────────────────────────
EXPERIMENT_STATUSES = (
    "created",
    "running",
    "completed",
    "failed",
    "interrupted",
)


# ─────────────────────────────────────────────────────────────────────────────
# Experiment dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Experiment:
    """
    Full metadata record for one training run.

    All mutable fields are updated in-place as the run progresses; call
    ``save()`` to persist the current state to disk.

    Attributes
    ----------
    experiment_id : str
        Unique identifier (UUID4 hex prefix + timestamp, e.g.
        ``"a3f2b1c0-20240715-143022"``).
    architecture : str
        Model architecture key.
    status : str
        One of "created" | "running" | "completed" | "failed" | "interrupted".
    created_at : str
        ISO-8601 UTC timestamp when the experiment was created.
    started_at : str | None
        When training began.
    finished_at : str | None
        When training finished (or failed).
    duration_s : float | None
        Wall-clock training duration in seconds.
    config : dict
        Serialised TrainingConfig snapshot.
    dataset_info : dict
        Dataset provenance: directory, split counts, class names, etc.
    phase1_history : dict
        Per-epoch metrics from Phase 1 (head training).
    phase2_history : dict
        Per-epoch metrics from Phase 2 (fine-tuning).
    eval_metrics : dict
        Post-training evaluation metrics from evaluate_model().
    model_paths : dict
        Paths to saved artefacts: model_dir, h5_path, checkpoint_path.
    error : str | None
        Exception message when status is "failed".
    notes : str
        Free-form notes field for tagging / annotation.
    """

    experiment_id: str
    architecture:  str
    status:        str = "created"
    created_at:    str = field(default_factory=lambda: _now_iso())
    started_at:    Optional[str] = None
    finished_at:   Optional[str] = None
    duration_s:    Optional[float] = None
    config:        Dict[str, Any] = field(default_factory=dict)
    dataset_info:  Dict[str, Any] = field(default_factory=dict)
    phase1_history: Dict[str, Any] = field(default_factory=dict)
    phase2_history: Dict[str, Any] = field(default_factory=dict)
    eval_metrics:  Dict[str, Any] = field(default_factory=dict)
    model_paths:   Dict[str, Any] = field(default_factory=dict)
    error:         Optional[str] = None
    notes:         str = ""

    # ── Computed path (not stored in JSON) ────────────────────────────────────
    _experiments_dir: Optional[Path] = field(default=None, repr=False, compare=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Factory
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        cfg: TrainingConfig,
        *,
        experiments_dir: Optional[Path] = None,
        notes: str = "",
    ) -> "Experiment":
        """
        Create a new Experiment from a TrainingConfig.

        Parameters
        ----------
        cfg : TrainingConfig
            Configuration for this run.
        experiments_dir : Path | None
            Override default storage location.
        notes : str
            Optional free-form annotation.

        Returns
        -------
        Experiment
            Status = "created".  Not yet saved to disk; call ``save()``.
        """
        ts  = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        uid = uuid.uuid4().hex[:8]
        exp_id = f"{cfg.architecture}-{ts}-{uid}"

        return cls(
            experiment_id=exp_id,
            architecture=cfg.architecture,
            status="created",
            config=cfg.to_dict(),
            notes=notes,
            _experiments_dir=experiments_dir,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Mutation helpers
    # ─────────────────────────────────────────────────────────────────────────

    def update_status(self, status: str) -> None:
        if status not in EXPERIMENT_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Choose: {EXPERIMENT_STATUSES}")
        self.status = status
        if status == "running" and self.started_at is None:
            self.started_at = _now_iso()
        if status in ("completed", "failed", "interrupted"):
            self.finished_at = _now_iso()

    def record_dataset_info(self, info: Dict[str, Any]) -> None:
        """Attach dataset provenance dict."""
        self.dataset_info = info

    def record_phase_history(
        self,
        phase: int,
        history: Dict[str, Any],
    ) -> None:
        """Store per-epoch metric lists from ``model.fit().history``."""
        serialised = {
            k: [float(v) for v in vals]
            for k, vals in history.items()
        }
        if phase == 1:
            self.phase1_history = serialised
        else:
            self.phase2_history = serialised

    def record_eval_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store post-training evaluation results."""
        self.eval_metrics = metrics

    def record_model_paths(self, paths: Dict[str, Any]) -> None:
        """Record paths to saved artefacts."""
        self.model_paths = paths

    def record_error(self, exc: Exception) -> None:
        """Mark the experiment as failed and store the exception message."""
        self.error = f"{type(exc).__name__}: {exc}"
        self.update_status("failed")

    def set_duration(self, seconds: float) -> None:
        self.duration_s = round(seconds, 2)

    # ─────────────────────────────────────────────────────────────────────────
    # Summary properties
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def best_val_accuracy(self) -> Optional[float]:
        """Peak validation accuracy across both phases."""
        candidates = []
        for hist in (self.phase1_history, self.phase2_history):
            vals = hist.get("val_accuracy", [])
            if vals:
                candidates.append(max(vals))
        return max(candidates) if candidates else None

    @property
    def final_val_loss(self) -> Optional[float]:
        """Final validation loss from whichever phase ran last."""
        for hist in (self.phase2_history, self.phase1_history):
            vals = hist.get("val_loss", [])
            if vals:
                return vals[-1]
        return None

    @property
    def epochs_trained(self) -> int:
        """Total epochs run across both phases."""
        return (
            len(self.phase1_history.get("loss", []))
            + len(self.phase2_history.get("loss", []))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-safe dict (excludes private fields)."""
        d = asdict(self)
        d.pop("_experiments_dir", None)
        return d

    def to_summary(self) -> Dict[str, Any]:
        """Lightweight summary for registry listings."""
        return {
            "experiment_id":    self.experiment_id,
            "architecture":     self.architecture,
            "status":           self.status,
            "created_at":       self.created_at,
            "finished_at":      self.finished_at,
            "duration_s":       self.duration_s,
            "epochs_trained":   self.epochs_trained,
            "best_val_accuracy": self.best_val_accuracy,
            "notes":            self.notes,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def experiments_dir(self) -> Path:
        if self._experiments_dir:
            return self._experiments_dir
        return _default_experiments_dir()

    @property
    def experiment_dir(self) -> Path:
        return self.experiments_dir / self.experiment_id

    def save(self) -> Path:
        """
        Persist the full experiment record to
        ``<experiments_dir>/<experiment_id>/experiment.json``.

        Also saves a copy of the TrainingConfig as ``training_config.json``
        and updates the registry index.

        Returns
        -------
        Path
            Absolute path to ``experiment.json``.
        """
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        # Full experiment JSON
        exp_path = self.experiment_dir / "experiment.json"
        with open(exp_path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

        # Config sidecar (for quick inspection without loading the full record)
        cfg_path = self.experiment_dir / "training_config.json"
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(self.config, fh, indent=2)

        logger.info(f"Experiment saved → {exp_path}")

        # Update the registry
        ExperimentRegistry(self.experiments_dir).upsert(self)

        return exp_path

    @classmethod
    def load(
        cls,
        experiment_id: str,
        experiments_dir: Optional[Path] = None,
    ) -> "Experiment":
        """
        Load an Experiment from disk by ID.

        Parameters
        ----------
        experiment_id : str
        experiments_dir : Path | None

        Returns
        -------
        Experiment

        Raises
        ------
        FileNotFoundError
            When the experiment directory or JSON file does not exist.
        """
        base = experiments_dir or _default_experiments_dir()
        exp_path = base / experiment_id / "experiment.json"
        if not exp_path.exists():
            raise FileNotFoundError(
                f"Experiment '{experiment_id}' not found at {exp_path}"
            )
        with open(exp_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Remove private field before constructing
        data.pop("_experiments_dir", None)
        exp = cls(**{k: v for k, v in data.items()
                     if k in cls.__dataclass_fields__})  # type: ignore[attr-defined]
        exp._experiments_dir = base
        return exp


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

class ExperimentRegistry:
    """
    Maintains an ``experiment_registry.json`` index in *experiments_dir*.

    The registry stores lightweight summaries for fast listing without
    loading individual experiment files.

    Parameters
    ----------
    experiments_dir : Path | None
        Storage root.  Defaults to ``settings.log_dir / "experiments"``.
    """

    REGISTRY_FILENAME = "experiment_registry.json"

    def __init__(self, experiments_dir: Optional[Path] = None) -> None:
        self.experiments_dir = experiments_dir or _default_experiments_dir()
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.experiments_dir / self.REGISTRY_FILENAME

    # ── I/O ───────────────────────────────────────────────────────────────────

    def _load_raw(self) -> Dict[str, Any]:
        if not self._registry_path.exists():
            return {"experiments": []}
        try:
            with open(self._registry_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as exc:
            logger.warning(f"Could not read registry: {exc} — starting fresh")
            return {"experiments": []}

    def _save_raw(self, data: Dict[str, Any]) -> None:
        with open(self._registry_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    # ── Public API ────────────────────────────────────────────────────────────

    def upsert(self, experiment: "Experiment") -> None:
        """
        Insert or update the summary entry for *experiment*.

        If an entry with the same ``experiment_id`` already exists it is
        replaced; otherwise a new entry is appended.
        """
        data = self._load_raw()
        entries: List[Dict[str, Any]] = data.get("experiments", [])
        summary = experiment.to_summary()

        # Replace existing entry or append
        replaced = False
        for i, entry in enumerate(entries):
            if entry.get("experiment_id") == experiment.experiment_id:
                entries[i] = summary
                replaced = True
                break
        if not replaced:
            entries.append(summary)

        # Keep sorted: newest first
        entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)
        data["experiments"] = entries
        self._save_raw(data)

    def list_experiments(
        self,
        *,
        architecture: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Return summary entries from the registry.

        Parameters
        ----------
        architecture : str | None
            Filter by architecture name.
        status : str | None
            Filter by experiment status.
        limit : int
            Maximum number of entries to return.

        Returns
        -------
        list[dict]
            Sorted newest-first.
        """
        entries = self._load_raw().get("experiments", [])
        if architecture:
            entries = [e for e in entries if e.get("architecture") == architecture]
        if status:
            entries = [e for e in entries if e.get("status") == status]
        return entries[:limit]

    def get(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the full experiment dict for *experiment_id* by loading its
        individual JSON file (not just the registry summary).

        Returns None when not found.
        """
        try:
            exp = Experiment.load(experiment_id, self.experiments_dir)
            return exp.to_dict()
        except FileNotFoundError:
            return None

    def delete(self, experiment_id: str, *, confirm: bool = False) -> bool:
        """
        Remove an experiment from the registry index (does NOT delete files).

        Parameters
        ----------
        confirm : bool
            Must be True to execute (safety guard).
        """
        if not confirm:
            return False
        data = self._load_raw()
        original_len = len(data["experiments"])
        data["experiments"] = [
            e for e in data["experiments"]
            if e.get("experiment_id") != experiment_id
        ]
        if len(data["experiments"]) < original_len:
            self._save_raw(data)
            logger.info(f"Experiment '{experiment_id}' removed from registry")
            return True
        return False

    def stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about all recorded experiments."""
        entries = self._load_raw().get("experiments", [])
        status_counts: Dict[str, int] = {}
        arch_counts:   Dict[str, int] = {}
        for entry in entries:
            s = entry.get("status", "unknown")
            a = entry.get("architecture", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
            arch_counts[a]   = arch_counts.get(a, 0) + 1

        accuracies = [
            e["best_val_accuracy"]
            for e in entries
            if e.get("best_val_accuracy") is not None
        ]
        return {
            "total":          len(entries),
            "by_status":      status_counts,
            "by_architecture": arch_counts,
            "best_accuracy":  max(accuracies) if accuracies else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_experiments_dir() -> Path:
    d = settings.log_dir / "experiments"
    d.mkdir(parents=True, exist_ok=True)
    return d

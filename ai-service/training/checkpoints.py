"""
training/checkpoints.py — Checkpoint lifecycle helpers.

Provides functions for saving, loading, listing, and deleting model
checkpoints independently of the main training loop.

Directory layout written by this module
----------------------------------------
    <output_dir>/
        <architecture>/
            checkpoints/
                <experiment_id>/
                    best_weights.h5
                    checkpoint_info.json   ← metadata snapshot

Usage
-----
    from training.checkpoints import save_checkpoint_info, load_best_weights
    from training.config import TrainingConfig

    cfg = TrainingConfig(architecture="resnet50")
    save_checkpoint_info(cfg, experiment_id="exp-001", metrics={"val_accuracy": 0.97})
    success = load_best_weights(model, cfg, experiment_id="exp-001")
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import tensorflow as tf

from app.core.logging import logger
from training.config import TrainingConfig


# ─── Path helpers ──────────────────────────────────────────────────────────────

def checkpoint_dir(cfg: TrainingConfig, experiment_id: str) -> Path:
    """Return the directory holding checkpoints for one experiment."""
    return cfg.resolved_output_dir / cfg.architecture / "checkpoints" / experiment_id


def best_weights_path(cfg: TrainingConfig, experiment_id: str) -> Path:
    """Return the absolute path to best_weights.weights.h5.

    Keras 3 (TF 2.16+) requires ``.weights.h5`` suffix when using
    ``save_weights_only=True`` in ``ModelCheckpoint``.
    """
    return checkpoint_dir(cfg, experiment_id) / "best_weights.weights.h5"


def checkpoint_info_path(cfg: TrainingConfig, experiment_id: str) -> Path:
    """Return the absolute path to checkpoint_info.json."""
    return checkpoint_dir(cfg, experiment_id) / "checkpoint_info.json"


# ─── Save ─────────────────────────────────────────────────────────────────────

def save_checkpoint_info(
    cfg: TrainingConfig,
    experiment_id: str,
    *,
    metrics: Optional[Dict[str, Any]] = None,
    epoch: Optional[int] = None,
    phase: int = 1,
) -> Path:
    """
    Write a ``checkpoint_info.json`` sidecar next to ``best_weights.h5``.

    Parameters
    ----------
    cfg : TrainingConfig
    experiment_id : str
    metrics : dict | None
        Metric snapshot at the best epoch (e.g. ``{"val_accuracy": 0.97}``).
    epoch : int | None
        The best epoch number (0-indexed).
    phase : int
        Training phase that produced this checkpoint.

    Returns
    -------
    Path
        Absolute path to the written JSON file.
    """
    ckpt_dir = checkpoint_dir(cfg, experiment_id)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    info_path = checkpoint_info_path(cfg, experiment_id)

    info: Dict[str, Any] = {
        "experiment_id":  experiment_id,
        "architecture":   cfg.architecture,
        "phase":          phase,
        "epoch":          epoch,
        "metrics":        metrics or {},
        "weights_path":   str(best_weights_path(cfg, experiment_id)),
        "saved_at":       datetime.now(timezone.utc).isoformat(),
        "config_summary": {
            "learning_rate":  cfg.learning_rate,
            "batch_size":     cfg.batch_size,
            "image_size":     cfg.image_size,
            "fine_tune":      cfg.fine_tune,
        },
    }

    with open(info_path, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)

    logger.info(f"Checkpoint info saved → {info_path}")
    return info_path


# ─── Load ─────────────────────────────────────────────────────────────────────

def load_best_weights(
    model: tf.keras.Model,
    cfg: TrainingConfig,
    experiment_id: str,
) -> bool:
    """
    Load ``best_weights.h5`` into *model* in-place.

    Parameters
    ----------
    model : tf.keras.Model
        A compiled model whose architecture matches the checkpoint.
    cfg : TrainingConfig
    experiment_id : str

    Returns
    -------
    bool
        True when weights were loaded; False when no checkpoint exists.
    """
    path = best_weights_path(cfg, experiment_id)
    if not path.exists():
        logger.warning(f"No checkpoint found at {path}")
        return False

    try:
        model.load_weights(str(path))
        logger.info(f"Best weights loaded from {path}")
        return True
    except Exception as exc:
        logger.error(f"Failed to load checkpoint from {path}: {exc}")
        return False


def load_checkpoint_info(
    cfg: TrainingConfig,
    experiment_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Return the ``checkpoint_info.json`` for one experiment, or None.

    Parameters
    ----------
    cfg : TrainingConfig
    experiment_id : str

    Returns
    -------
    dict | None
    """
    path = checkpoint_info_path(cfg, experiment_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning(f"Could not read checkpoint info at {path}: {exc}")
        return None


# ─── List / delete ────────────────────────────────────────────────────────────

def list_checkpoints(cfg: TrainingConfig) -> List[Dict[str, Any]]:
    """
    List all experiment checkpoints for one architecture.

    Returns a list of checkpoint info dicts (from ``checkpoint_info.json``),
    sorted by ``saved_at`` descending (newest first).

    Parameters
    ----------
    cfg : TrainingConfig

    Returns
    -------
    list[dict]
    """
    arch_dir = cfg.resolved_output_dir / cfg.architecture / "checkpoints"
    if not arch_dir.exists():
        return []

    results = []
    for exp_dir in arch_dir.iterdir():
        if not exp_dir.is_dir():
            continue
        info_file = exp_dir / "checkpoint_info.json"
        weights_file = exp_dir / "best_weights.h5"
        entry: Dict[str, Any] = {"experiment_id": exp_dir.name}
        if info_file.exists():
            try:
                with open(info_file, "r", encoding="utf-8") as fh:
                    entry.update(json.load(fh))
            except Exception:
                pass
        entry["weights_exist"] = weights_file.exists()
        results.append(entry)

    results.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    return results


def delete_checkpoint(
    cfg: TrainingConfig,
    experiment_id: str,
    *,
    confirm: bool = False,
) -> bool:
    """
    Delete the checkpoint directory for *experiment_id*.

    Parameters
    ----------
    cfg : TrainingConfig
    experiment_id : str
    confirm : bool
        Must be True to actually delete (safety guard).

    Returns
    -------
    bool
        True when deletion succeeded.
    """
    if not confirm:
        logger.warning(
            "delete_checkpoint() called without confirm=True — no action taken."
        )
        return False

    path = checkpoint_dir(cfg, experiment_id)
    if not path.exists():
        logger.warning(f"Checkpoint directory does not exist: {path}")
        return False

    try:
        shutil.rmtree(path)
        logger.info(f"Checkpoint deleted: {path}")
        return True
    except Exception as exc:
        logger.error(f"Failed to delete checkpoint at {path}: {exc}")
        return False

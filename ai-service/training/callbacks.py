"""
training/callbacks.py — Callback factory for the training pipeline.

All callbacks are built from a single ``TrainingConfig`` so that every
experiment uses the same logic and the configuration is fully reproducible.

Callbacks produced
------------------
1. ModelCheckpoint     — saves best-epoch weights to
                         ``<output_dir>/<arch>/checkpoints/best_weights.h5``
2. EarlyStopping       — stops training when ``val_loss`` stagnates
3. ReduceLROnPlateau   — halves LR when ``val_loss`` plateaus
4. TensorBoard         — event logs at ``<log_dir>/tensorboard/<arch>/``
5. CSVLogger           — per-epoch CSV at ``<log_dir>/training/<arch>.csv``
                         (only when ``cfg.csv_log`` is True)

Usage
-----
    from training.config import TrainingConfig
    from training.callbacks import build_callbacks

    cfg = TrainingConfig(architecture="resnet50")
    cb  = build_callbacks(cfg, experiment_id="exp-001")
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import tensorflow as tf

from app.core.config import settings
from app.core.logging import logger
from training.config import TrainingConfig


def _checkpoint_path(cfg: TrainingConfig, experiment_id: str) -> Path:
    """Return the path where best-epoch weights are written.

    Keras 3 (TF 2.16+) requires the filename to end in ``.weights.h5``
    when ``save_weights_only=True``.
    """
    base = cfg.resolved_output_dir
    ckpt_dir = base / cfg.architecture / "checkpoints" / experiment_id
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    return ckpt_dir / "best_weights.weights.h5"


def _csv_log_path(cfg: TrainingConfig, experiment_id: str) -> Path:
    """Return the path for the CSVLogger output file."""
    log_dir = settings.log_dir / "training"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{experiment_id}.csv"


def _tensorboard_log_dir(cfg: TrainingConfig, experiment_id: str) -> Path:
    """Return the TensorBoard log directory."""
    tb_dir = settings.log_dir / "tensorboard" / experiment_id
    tb_dir.mkdir(parents=True, exist_ok=True)
    return tb_dir


def build_callbacks(
    cfg: TrainingConfig,
    experiment_id: str,
    *,
    phase: int = 1,
    extra: Optional[List[tf.keras.callbacks.Callback]] = None,
) -> List[tf.keras.callbacks.Callback]:
    """
    Build the full callback stack for one training phase.

    Parameters
    ----------
    cfg : TrainingConfig
        Training configuration (drives patience, LR schedule, paths).
    experiment_id : str
        Unique experiment identifier used to namespace log files.
    phase : int
        Training phase (1 = head training, 2 = fine-tuning).
        Phase 2 uses a tighter EarlyStopping patience
        (``cfg.early_stopping_patience // 2 + 3``).
    extra : list[Callback] | None
        Any additional callbacks to append (e.g. custom metric loggers).

    Returns
    -------
    list[tf.keras.callbacks.Callback]
        Ready to pass directly to ``model.fit(callbacks=...)``.
    """
    callbacks: List[tf.keras.callbacks.Callback] = []

    # ── 1. ModelCheckpoint ────────────────────────────────────────────────────
    ckpt_path = _checkpoint_path(cfg, experiment_id)
    ckpt_cb = tf.keras.callbacks.ModelCheckpoint(
        filepath=str(ckpt_path),
        monitor="val_accuracy",
        save_best_only=True,
        save_weights_only=True,
        mode="max",
        verbose=1,
    )
    callbacks.append(ckpt_cb)
    logger.debug(f"ModelCheckpoint → {ckpt_path}")

    # ── 2. EarlyStopping ──────────────────────────────────────────────────────
    # Phase 2 is already converging close to the optimum — use tighter patience
    es_patience = (
        cfg.early_stopping_patience
        if phase == 1
        else max(cfg.early_stopping_patience // 2, 3)
    )
    es_cb = tf.keras.callbacks.EarlyStopping(
        monitor=cfg.early_stopping_monitor,
        patience=es_patience,
        min_delta=1e-4,
        restore_best_weights=True,
        verbose=1,
    )
    callbacks.append(es_cb)

    # ── 3. ReduceLROnPlateau ──────────────────────────────────────────────────
    rlr_cb = tf.keras.callbacks.ReduceLROnPlateau(
        monitor=cfg.early_stopping_monitor,
        factor=cfg.reduce_lr_factor,
        patience=cfg.reduce_lr_patience,
        min_lr=cfg.reduce_lr_min,
        verbose=1,
    )
    callbacks.append(rlr_cb)

    # ── 4. TensorBoard ────────────────────────────────────────────────────────
    tb_dir = _tensorboard_log_dir(cfg, experiment_id)
    tb_cb = tf.keras.callbacks.TensorBoard(
        log_dir=str(tb_dir / f"phase{phase}"),
        histogram_freq=1,
        write_graph=False,
        update_freq="epoch",
    )
    callbacks.append(tb_cb)
    logger.debug(f"TensorBoard → {tb_dir / f'phase{phase}'}")

    # ── 5. CSVLogger (optional) ───────────────────────────────────────────────
    if cfg.csv_log:
        csv_path = _csv_log_path(cfg, f"{experiment_id}_phase{phase}")
        csv_cb = tf.keras.callbacks.CSVLogger(
            filename=str(csv_path),
            separator=",",
            append=False,
        )
        callbacks.append(csv_cb)
        logger.debug(f"CSVLogger → {csv_path}")

    # ── Extra callbacks ───────────────────────────────────────────────────────
    if extra:
        callbacks.extend(extra)

    logger.info(
        f"Callbacks built | experiment={experiment_id} phase={phase} "
        f"es_patience={es_patience} n_callbacks={len(callbacks)}"
    )
    return callbacks


def get_best_checkpoint_path(
    cfg: TrainingConfig,
    experiment_id: str,
) -> Optional[Path]:
    """
    Return the path to the best checkpoint if it exists, else None.

    Parameters
    ----------
    cfg : TrainingConfig
    experiment_id : str

    Returns
    -------
    Path | None
    """
    p = _checkpoint_path(cfg, experiment_id)
    return p if p.exists() else None

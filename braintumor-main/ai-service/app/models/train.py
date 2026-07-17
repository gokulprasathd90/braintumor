"""
train.py — Full model training pipeline.

Two-phase transfer learning strategy
--------------------------------------
Phase 1  Frozen backbone, train only the classification head for ``epochs``
         epochs with learning_rate.  Stops early via EarlyStopping.
Phase 2  Unfreeze the top ``fine_tune_layers`` of the backbone, continue
         for ``fine_tune_epochs`` at ``fine_tune_lr`` (default: lr / 10).

Usage
-----
    from app.models.train import train_model
    result = train_model("efficientnet", epochs=30, batch_size=32)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import tensorflow as tf

from app.core.config import settings
from app.core.logging import logger
from app.models.architectures import build_model, unfreeze_top_layers
from app.models.save_model import save_keras_model, save_best_checkpoint_callback
from app.preprocessing.preprocess import build_data_generators


# ─── Callback factory ─────────────────────────────────────────────────────────

def _build_callbacks(
    model_name: str,
    *,
    patience: int = 10,
    min_delta: float = 1e-4,
) -> List[tf.keras.callbacks.Callback]:
    """
    Return the standard callback stack for training.

    Callbacks
    ---------
    - ModelCheckpoint  — saves best val_accuracy weights to disk
    - EarlyStopping    — halts training when val_loss stops improving
    - ReduceLROnPlateau — halves LR after ``patience//2`` stagnant epochs
    - TensorBoard      — writes event logs to logs/tensorboard/<model_name>/
    """
    callbacks: List[tf.keras.callbacks.Callback] = [
        # Best-weights checkpoint (from save_model.py)
        save_best_checkpoint_callback(model_name, monitor="val_accuracy"),

        # Early stopping on validation loss
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=patience,
            min_delta=min_delta,
            restore_best_weights=True,
            verbose=1,
        ),

        # Reduce LR on plateau
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=max(patience // 2, 3),
            min_lr=1e-7,
            verbose=1,
        ),

        # TensorBoard logs
        tf.keras.callbacks.TensorBoard(
            log_dir=str(settings.log_dir / "tensorboard" / model_name),
            histogram_freq=1,
            write_graph=False,
        ),
    ]
    return callbacks


# ─── History helper ───────────────────────────────────────────────────────────

def _extract_final_metrics(history: tf.keras.callbacks.History) -> Dict[str, float]:
    """Pull the last-epoch metrics out of a Keras History object."""
    hist = history.history
    return {
        "final_train_loss":     float(hist["loss"][-1]),
        "final_train_accuracy": float(hist["accuracy"][-1]),
        "final_val_loss":       float(hist.get("val_loss", [0.0])[-1]),
        "final_val_accuracy":   float(hist.get("val_accuracy", [0.0])[-1]),
        "epochs_run":           len(hist["loss"]),
    }


# ─── Public training entry point ─────────────────────────────────────────────

def train_model(
    model_name: str = "efficientnet",
    epochs: int = 30,
    batch_size: int = 32,
    learning_rate: float = 1e-4,
    dataset_dir: Optional[str] = None,
    *,
    validation_split: float = 0.2,
    fine_tune: bool = True,
    fine_tune_layers: int = 20,
    fine_tune_epochs: int = 10,
    fine_tune_lr: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Train a deep learning model on MRI brain tumour images.

    Parameters
    ----------
    model_name : str
        Architecture — "cnn" | "vgg16" | "resnet50" | "efficientnet".
    epochs : int
        Max Phase-1 epochs (EarlyStopping may cut short).
    batch_size : int
        Mini-batch size for both train and validation generators.
    learning_rate : float
        Phase-1 learning rate (Adam).
    dataset_dir : str | None
        Root directory containing one sub-folder per class.
        Falls back to ``settings.dataset_raw_dir``.
    validation_split : float
        Fraction of training data reserved for validation (default 0.2).
    fine_tune : bool
        Whether to run Phase-2 fine-tuning after Phase-1 converges.
        Ignored for the custom CNN (no frozen backbone to unfreeze).
    fine_tune_layers : int
        Number of backbone layers to unfreeze in Phase 2.
    fine_tune_epochs : int
        Additional epochs for Phase 2.
    fine_tune_lr : float | None
        Phase-2 learning rate. Defaults to ``learning_rate / 10``.

    Returns
    -------
    dict
        {
          "model_name":           str,
          "epochs_phase1":        int,
          "epochs_phase2":        int,
          "final_train_accuracy": float,
          "final_val_accuracy":   float,
          "final_train_loss":     float,
          "final_val_loss":       float,
          "training_duration_s":  float,
          "saved_paths":          dict,
          "phase1_history":       dict,   # full per-epoch logs
          "phase2_history":       dict,
        }

    Raises
    ------
    FileNotFoundError
        When the dataset directory does not exist.
    """
    name         = model_name.lower()
    data_dir     = Path(dataset_dir) if dataset_dir else settings.dataset_raw_dir
    ft_lr        = fine_tune_lr or (learning_rate / 10)

    logger.info(
        f"Training started | model={name} epochs={epochs} "
        f"batch={batch_size} lr={learning_rate} dataset={data_dir}"
    )

    # ── Data generators ───────────────────────────────────────────────────────
    train_gen, val_gen = build_data_generators(
        data_dir,
        batch_size=batch_size,
        validation_split=validation_split,
    )

    # ── Build model ───────────────────────────────────────────────────────────
    model = build_model(name, learning_rate=learning_rate)

    # ── Phase 1 — train classification head only ──────────────────────────────
    t0 = time.perf_counter()
    logger.info(f"Phase 1: training head | max_epochs={epochs}")

    callbacks_p1 = _build_callbacks(name, patience=10)

    history_p1 = model.fit(
        train_gen,
        epochs=epochs,
        validation_data=val_gen,
        callbacks=callbacks_p1,
        verbose=1,
    )

    metrics_p1    = _extract_final_metrics(history_p1)
    phase1_epochs = metrics_p1["epochs_run"]

    logger.info(
        f"Phase 1 complete | "
        f"val_acc={metrics_p1['final_val_accuracy']:.4f} "
        f"epochs={phase1_epochs}"
    )

    # ── Phase 2 — fine-tune top backbone layers ───────────────────────────────
    metrics_p2    = {}
    history_p2_dict: Dict[str, Any] = {}
    phase2_epochs = 0

    if fine_tune and name != "cnn":
        logger.info(
            f"Phase 2: fine-tuning top {fine_tune_layers} layers | "
            f"max_epochs={fine_tune_epochs} lr={ft_lr}"
        )

        model = unfreeze_top_layers(model, n_layers=fine_tune_layers)
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=ft_lr),
            loss="categorical_crossentropy",
            metrics=[
                "accuracy",
                tf.keras.metrics.AUC(name="auc"),
                tf.keras.metrics.Precision(name="precision"),
                tf.keras.metrics.Recall(name="recall"),
            ],
        )

        callbacks_p2 = _build_callbacks(name, patience=7)

        history_p2 = model.fit(
            train_gen,
            epochs=fine_tune_epochs,
            validation_data=val_gen,
            callbacks=callbacks_p2,
            verbose=1,
        )

        metrics_p2    = _extract_final_metrics(history_p2)
        phase2_epochs = metrics_p2["epochs_run"]
        history_p2_dict = {k: [float(v) for v in vals]
                           for k, vals in history_p2.history.items()}

        logger.info(
            f"Phase 2 complete | "
            f"val_acc={metrics_p2['final_val_accuracy']:.4f} "
            f"epochs={phase2_epochs}"
        )

    duration_s = time.perf_counter() - t0

    # ── Save model + metadata ─────────────────────────────────────────────────
    best_val_acc = (
        metrics_p2.get("final_val_accuracy")
        or metrics_p1["final_val_accuracy"]
    )

    saved_paths = save_keras_model(
        model,
        name,
        metadata={
            "epochs_phase1":        phase1_epochs,
            "epochs_phase2":        phase2_epochs,
            "final_val_accuracy":   best_val_acc,
            "final_val_loss":       (
                metrics_p2.get("final_val_loss")
                or metrics_p1["final_val_loss"]
            ),
            "training_duration_s":  round(duration_s, 2),
            "learning_rate":        learning_rate,
            "batch_size":           batch_size,
            "fine_tuned":           fine_tune and name != "cnn",
        },
    )

    logger.info(
        f"Training complete | model={name} "
        f"val_acc={best_val_acc:.4f} "
        f"duration={duration_s:.1f}s"
    )

    return {
        "model_name":           name,
        "epochs_phase1":        phase1_epochs,
        "epochs_phase2":        phase2_epochs,
        "final_train_accuracy": metrics_p1["final_train_accuracy"],
        "final_val_accuracy":   best_val_acc,
        "final_train_loss":     metrics_p1["final_train_loss"],
        "final_val_loss":       (
            metrics_p2.get("final_val_loss")
            or metrics_p1["final_val_loss"]
        ),
        "training_duration_s":  round(duration_s, 2),
        "saved_paths":          saved_paths,
        "phase1_history":       {k: [float(v) for v in vals]
                                  for k, vals in history_p1.history.items()},
        "phase2_history":       history_p2_dict,
    }

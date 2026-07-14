"""
save_model.py — Keras model persistence with companion metadata.

Each model is written to::

    saved_models/<model_name>/
        saved_model.pb          ← TF SavedModel (default)
        variables/
        model_info.json         ← training metadata snapshot
    saved_models/<model_name>/<model_name>.h5   ← optional HDF5 copy

The ``model_info.json`` file is read back by ``load_model.get_model_info()``
and surfaced through the /evaluate and /health endpoints.

Usage
-----
    from app.models.save_model import save_keras_model
    paths = save_keras_model(model, "efficientnet", val_accuracy=0.973)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import tensorflow as tf

from app.core.config import settings
from app.core.logging import logger


def save_keras_model(
    model: tf.keras.Model,
    model_name: str,
    *,
    output_dir: Optional[str | Path] = None,
    save_format: str = "tf",
    also_save_h5: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Persist a trained Keras model to disk with a metadata JSON sidecar.

    Parameters
    ----------
    model : tf.keras.Model
        The trained model to save.
    model_name : str
        Sub-directory name under ``saved_models/`` (e.g. ``"efficientnet"``).
    output_dir : str | Path | None
        Override the default ``settings.saved_models_dir``.
    save_format : str
        ``"tf"`` (SavedModel, recommended) or ``"h5"``.
    also_save_h5 : bool
        When *save_format* is ``"tf"``, also write a ``.h5`` file alongside
        for portability (useful for sharing weights without the full TF runtime).
    metadata : dict | None
        Arbitrary key/value pairs to include in ``model_info.json``
        (e.g. val_accuracy, epochs, training_duration_s).

    Returns
    -------
    dict
        {
            "model_dir":    str,   # absolute path to the SavedModel dir
            "model_path":   str,   # absolute path to the primary artefact
            "h5_path":      str,   # absolute path to the .h5 file (or "")
            "info_path":    str,   # absolute path to model_info.json
            "format":       str,
        }

    Raises
    ------
    ValueError
        If *save_format* is not "tf" or "h5".
    RuntimeError
        If TensorFlow fails to serialise the model.
    """
    if save_format not in {"tf", "h5"}:
        raise ValueError(f"save_format must be 'tf' or 'h5', got '{save_format}'")

    name      = model_name.lower()
    base_dir  = Path(output_dir) if output_dir else settings.saved_models_dir
    model_dir = base_dir / name
    model_dir.mkdir(parents=True, exist_ok=True)

    # ── Primary artefact ──────────────────────────────────────────────────────
    if save_format == "tf":
        model_path = model_dir  # SavedModel is a directory
        try:
            model.save(str(model_path), save_format="tf")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to save model '{name}' as SavedModel: {exc}"
            ) from exc
        logger.info(f"Model '{name}' saved as SavedModel → {model_path}")
    else:
        model_path = model_dir / f"{name}.h5"
        try:
            model.save(str(model_path), save_format="h5")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to save model '{name}' as HDF5: {exc}"
            ) from exc
        logger.info(f"Model '{name}' saved as HDF5 → {model_path}")

    # ── Optional .h5 copy (when primary is SavedModel) ────────────────────────
    h5_path_str = ""
    if save_format == "tf" and also_save_h5:
        h5_path = model_dir / f"{name}.h5"
        try:
            model.save(str(h5_path), save_format="h5")
            h5_path_str = str(h5_path)
            logger.info(f"Also saved HDF5 copy → {h5_path}")
        except Exception as exc:
            # Non-fatal — log and continue
            logger.warning(f"Could not save HDF5 copy for '{name}': {exc}")

    # ── Metadata JSON ─────────────────────────────────────────────────────────
    info_path = model_dir / "model_info.json"
    model_info: Dict[str, Any] = {
        "model_name":    name,
        "save_format":   save_format,
        "input_shape":   list(settings.input_shape),
        "num_classes":   settings.num_classes,
        "class_names":   settings.classes,
        "total_params":  model.count_params(),
        "saved_at":      datetime.now(timezone.utc).isoformat(),
        "model_path":    str(model_path),
        "h5_path":       h5_path_str,
    }

    if metadata:
        model_info.update(metadata)

    try:
        with open(info_path, "w", encoding="utf-8") as fh:
            json.dump(model_info, fh, indent=2)
        logger.info(f"model_info.json written → {info_path}")
    except Exception as exc:
        logger.warning(f"Could not write model_info.json: {exc}")

    return {
        "model_dir":  str(model_dir),
        "model_path": str(model_path),
        "h5_path":    h5_path_str,
        "info_path":  str(info_path),
        "format":     save_format,
    }


def save_best_checkpoint_callback(
    model_name: str,
    *,
    monitor: str = "val_accuracy",
    output_dir: Optional[str | Path] = None,
) -> tf.keras.callbacks.ModelCheckpoint:
    """
    Return a ``ModelCheckpoint`` callback that saves the best epoch weights.

    Writes to ``saved_models/<model_name>/checkpoints/best_weights.h5``.
    Used internally by ``train.py``.

    Parameters
    ----------
    model_name : str
        Sub-directory key under ``saved_models/``.
    monitor : str
        Metric to monitor (default ``"val_accuracy"``).
    output_dir : str | Path | None
        Override the default ``settings.saved_models_dir``.

    Returns
    -------
    tf.keras.callbacks.ModelCheckpoint
    """
    base_dir       = Path(output_dir) if output_dir else settings.saved_models_dir
    checkpoint_dir = base_dir / model_name.lower() / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "best_weights.weights.h5"

    logger.debug(f"Checkpoint callback → {checkpoint_path} (monitor={monitor})")

    return tf.keras.callbacks.ModelCheckpoint(
        filepath=str(checkpoint_path),
        monitor=monitor,
        save_best_only=True,
        save_weights_only=True,
        mode="max",
        verbose=1,
    )

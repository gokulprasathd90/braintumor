"""
evaluate.py — Model evaluation on the held-out test split.

Computes the full set of classification metrics using scikit-learn,
then returns them in a structured dict that maps directly to the
EvaluateResponse Pydantic schema in routes.py.

Usage
-----
    from app.models.evaluate import evaluate_model
    metrics = evaluate_model("efficientnet")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from app.core.config import settings
from app.core.logging import logger
from app.models.load_model import load_keras_model, get_model_info
from app.preprocessing.preprocess import build_test_generator


def evaluate_model(
    model_name: Optional[str] = None,
    dataset_dir: Optional[str] = None,
    batch_size: int = 32,
) -> Dict[str, Any]:
    """
    Evaluate a trained model against a test split and return metrics.

    The function expects a directory whose structure mirrors the training
    dataset (one sub-folder per class).  If a dedicated test split does
    not exist, point ``dataset_dir`` at the full dataset; the generator
    iterates without augmentation and without shuffling.

    Parameters
    ----------
    model_name : str | None
        Architecture key. Falls back to ``settings.active_model``.
    dataset_dir : str | None
        Root of the test/evaluation dataset. Defaults to
        ``settings.dataset_raw_dir`` (adjust via DATASET_RAW_DIR env var).
    batch_size : int
        Batch size for the evaluation loop.

    Returns
    -------
    dict
        {
          "model_name":       str,
          "accuracy":         float,
          "precision":        float,   # macro-averaged
          "recall":           float,   # macro-averaged
          "f1":               float,   # macro-averaged
          "auc_roc":          float,   # macro OvR
          "confusion_matrix": [[int, ...], ...],
          "per_class":        {label: {"precision", "recall", "f1", "support"}, ...},
          "num_samples":      int,
          "class_names":      [str, ...],
          "model_info":       dict,    # from model_info.json
        }

    Raises
    ------
    FileNotFoundError
        When the dataset directory or model weights are not found.
    """
    name      = (model_name or settings.active_model).lower()
    data_dir  = Path(dataset_dir) if dataset_dir else settings.dataset_raw_dir
    classes   = settings.classes

    logger.info(f"Evaluation started | model={name} dataset={data_dir}")

    # ── Load model ────────────────────────────────────────────────────────────
    model = load_keras_model(name)

    # ── Build test generator ──────────────────────────────────────────────────
    test_gen = build_test_generator(
        data_dir,
        batch_size=batch_size,
        target_size=settings.image_size,
    )

    num_samples = test_gen.samples
    if num_samples == 0:
        raise ValueError(
            f"No images found in {data_dir}. "
            "Ensure the dataset directory contains class sub-folders."
        )

    # ── Run predictions ───────────────────────────────────────────────────────
    logger.info(f"Running predictions on {num_samples} test samples …")
    raw_preds: np.ndarray = model.predict(test_gen, verbose=1)  # (N, num_classes)

    y_pred_indices: np.ndarray = np.argmax(raw_preds, axis=1)
    y_true_indices: np.ndarray = test_gen.classes

    # Map class folder indices to our canonical class list
    # (generator may order folders alphabetically — re-map via class_indices)
    gen_class_map: Dict[str, int] = test_gen.class_indices  # {"glioma": 0, ...}
    canonical_map: Dict[int, int] = {
        gen_idx: classes.index(cls_name)
        for cls_name, gen_idx in gen_class_map.items()
        if cls_name in classes
    }

    y_true = np.array([canonical_map.get(i, i) for i in y_true_indices])
    y_pred = np.array([canonical_map.get(i, i) for i in y_pred_indices])

    # Reorder raw_preds columns to match canonical class order
    col_order: List[int] = [
        gen_class_map[cls] for cls in classes if cls in gen_class_map
    ]
    probs_canonical = raw_preds[:, col_order]

    # ── Scalar metrics ────────────────────────────────────────────────────────
    accuracy  = float(accuracy_score(y_true, y_pred))
    precision = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    recall    = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1        = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    # AUC-ROC (macro OvR — requires probability scores)
    try:
        auc_roc = float(
            roc_auc_score(y_true, probs_canonical, multi_class="ovr", average="macro")
        )
    except ValueError as exc:
        logger.warning(f"AUC-ROC computation failed: {exc}")
        auc_roc = 0.0

    # ── Confusion matrix ──────────────────────────────────────────────────────
    cm: np.ndarray = confusion_matrix(y_true, y_pred, labels=list(range(len(classes))))
    cm_list: List[List[int]] = cm.tolist()

    # ── Per-class metrics ──────────────────────────────────────────────────────
    report: Dict[str, Any] = classification_report(
        y_true,
        y_pred,
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )

    per_class: Dict[str, Dict[str, float]] = {
        cls: {
            "precision": round(float(report[cls]["precision"]), 4),
            "recall":    round(float(report[cls]["recall"]), 4),
            "f1":        round(float(report[cls]["f1-score"]), 4),
            "support":   int(report[cls]["support"]),
        }
        for cls in classes
        if cls in report
    }

    logger.info(
        f"Evaluation complete | model={name} "
        f"accuracy={accuracy:.4f} f1={f1:.4f} auc_roc={auc_roc:.4f}"
    )

    return {
        "model_name":       name,
        "accuracy":         round(accuracy, 4),
        "precision":        round(precision, 4),
        "recall":           round(recall, 4),
        "f1":               round(f1, 4),
        "auc_roc":          round(auc_roc, 4),
        "confusion_matrix": cm_list,
        "per_class":        per_class,
        "num_samples":      num_samples,
        "class_names":      classes,
        "model_info":       get_model_info(name),
    }

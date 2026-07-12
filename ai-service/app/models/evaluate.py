"""
evaluate.py — Model evaluation placeholder.

This module will compute classification metrics (accuracy, precision,
recall, F1, AUC-ROC, confusion matrix) on the held-out test split once
the model and dataset are available.

TODO (next phase):
    - Load test data generator
    - Load model via load_model.py
    - Run model.evaluate() and model.predict()
    - Compute per-class metrics with scikit-learn
    - Produce confusion matrix and ROC curves (matplotlib)
    - Return structured EvaluationResult
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def evaluate_model(
    model_name: Optional[str] = None,
    dataset_dir: Optional[str] = None,
    batch_size: int = 32,
) -> Dict[str, Any]:
    """
    Evaluate a trained model against the test split.

    Parameters
    ----------
    model_name : str | None
        Architecture to evaluate.  Falls back to settings.active_model.
    dataset_dir : str | None
        Path to the dataset root.  Uses config default when None.
    batch_size : int
        Batch size for the evaluation loop.

    Returns
    -------
    dict
        {
            "accuracy":  float,
            "precision": float,
            "recall":    float,
            "f1":        float,
            "auc_roc":   float,
            "confusion_matrix": [[int, ...], ...],
            "per_class": {label: {"precision": float, ...}, ...},
        }

    Raises
    ------
    NotImplementedError
        Placeholder — raised until the implementation is complete.
    """
    raise NotImplementedError(
        "evaluate_model() is not yet implemented. "
        "Evaluation logic will be added in the next phase."
    )

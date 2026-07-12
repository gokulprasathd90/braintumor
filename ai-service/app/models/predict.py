"""
predict.py — Inference placeholder.

This module will contain the full prediction pipeline once the model
architecture and weights are implemented.  Exposes the public function
signatures so the API layer can import them without error.

TODO (next phase):
    - Accept a raw image path or byte buffer
    - Run the same preprocessing as training (resize, normalise)
    - Load the active model via load_model.py
    - Call model.predict() and return softmax probabilities
    - Identify the top-1 class and confidence score
    - Generate Grad-CAM heatmap for explainability
    - Return structured PredictionResult
"""

from __future__ import annotations

from typing import Any, Dict


def predict(image_path: str, model_name: str | None = None) -> Dict[str, Any]:
    """
    Run inference on a single MRI image.

    Parameters
    ----------
    image_path : str
        Absolute path to the pre-processed PNG/JPEG image.
    model_name : str | None
        Model architecture to use.  Falls back to settings.active_model.

    Returns
    -------
    dict
        {
            "class":       str,   # predicted class label
            "confidence":  float, # probability 0–1
            "probabilities": {label: float, ...},
            "gradcam_path": str | None,
        }

    Raises
    ------
    NotImplementedError
        Placeholder — raised until the implementation is complete.
    """
    raise NotImplementedError(
        "predict() is not yet implemented. "
        "Inference logic will be added in the next phase."
    )

"""
load_model.py — Model loading placeholder.

This module will handle loading serialised Keras models (.h5 or SavedModel)
from the saved_models/ directory.  Uses a simple in-memory cache so the
model is loaded only once per process.

TODO (next phase):
    - Use tf.keras.models.load_model() to load .h5 / SavedModel artefacts
    - Implement a per-architecture cache (dict keyed by model_name)
    - Support hot-reload for production model swapping
    - Validate loaded model's input shape against current config
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Module-level model cache — populated when load_keras_model() is called
_model_cache: Dict[str, Any] = {}


def load_keras_model(model_name: Optional[str] = None) -> Any:
    """
    Load (and cache) a Keras model from the saved_models directory.

    Parameters
    ----------
    model_name : str | None
        Architecture key — "cnn" | "vgg16" | "resnet50" | "efficientnet".
        Defaults to settings.active_model when None.

    Returns
    -------
    tf.keras.Model
        The loaded model, ready for inference.

    Raises
    ------
    NotImplementedError
        Placeholder — raised until the implementation is complete.
    FileNotFoundError
        Raised (in future) when the model weights file does not exist.
    """
    raise NotImplementedError(
        "load_keras_model() is not yet implemented. "
        "Model loading will be added in the next phase."
    )


def clear_model_cache() -> None:
    """Evict all cached models from memory (useful for testing)."""
    _model_cache.clear()

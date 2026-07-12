"""
save_model.py — Model persistence placeholder.

This module will handle saving trained Keras models to the saved_models/
directory in both .h5 (legacy) and SavedModel formats.

TODO (next phase):
    - Accept a tf.keras.Model and a model_name key
    - Save to saved_models/<model_name>/ as a TF SavedModel (default)
    - Optionally also save as <model_name>.h5 for portability
    - Record metadata (training date, val_accuracy, config snapshot)
      alongside the weights in a model_info.json file
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def save_keras_model(
    model: Any,
    model_name: str,
    output_dir: Optional[str] = None,
    save_format: str = "tf",
) -> Dict[str, str]:
    """
    Persist a trained Keras model to disk.

    Parameters
    ----------
    model : tf.keras.Model
        The trained model to save.
    model_name : str
        Key used as the sub-directory name under saved_models/.
    output_dir : str | None
        Override the default saved_models directory.
    save_format : str
        "tf" (SavedModel) or "h5".

    Returns
    -------
    dict
        {"model_path": str, "format": str}

    Raises
    ------
    NotImplementedError
        Placeholder — raised until the implementation is complete.
    """
    raise NotImplementedError(
        "save_keras_model() is not yet implemented. "
        "Model saving will be added in the next phase."
    )

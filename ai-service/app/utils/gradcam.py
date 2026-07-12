"""
gradcam.py — Grad-CAM explainability placeholder.

Will generate Class Activation Map heatmaps using tf-explain once the
model architecture and weights are implemented.

TODO (next phase):
    - Load model via load_model.py
    - Use tf_explain.core.grad_cam.GradCAM to produce heatmaps
    - Overlay heatmap on the original MRI image with OpenCV
    - Save output to settings.gradcam_output_dir
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def generate_gradcam(
    image_path: str,
    model_name: Optional[str] = None,
    class_index: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate a Grad-CAM heatmap for an MRI image.

    Parameters
    ----------
    image_path : str
        Path to the preprocessed image.
    model_name : str | None
        Model architecture key. Defaults to settings.active_model.
    class_index : int | None
        Target class index. Defaults to the top-1 predicted class.

    Returns
    -------
    dict
        {"gradcam_path": str, "class_index": int}

    Raises
    ------
    NotImplementedError
        Placeholder — raised until the implementation is complete.
    """
    raise NotImplementedError(
        "generate_gradcam() is not yet implemented. "
        "Grad-CAM explainability will be added in the next phase."
    )

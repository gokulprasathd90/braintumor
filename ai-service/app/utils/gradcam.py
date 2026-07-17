"""
gradcam.py — Grad-CAM heatmap generation and overlay.

Uses TensorFlow's GradientTape to compute the gradient of the top predicted
class score with respect to the last convolutional feature map, then
overlays the resulting heatmap on the original MRI image.

This is a pure-TF implementation that does not depend on tf-explain
(which has compatibility issues with TF 2.x + Keras 3).  tf-explain is
retained in requirements.txt for future use but is not imported here.

Usage
-----
    from app.utils.gradcam import generate_gradcam
    result = generate_gradcam(image_bytes, model_name="efficientnet")
    # result["gradcam_path"] → absolute path to the saved overlay PNG
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np
import tensorflow as tf

from app.core.config import settings
from app.core.logging import logger
from app.models.load_model import load_keras_model
from app.preprocessing.preprocess import preprocess_image_for_gradcam


# ─── Last-conv-layer lookup ───────────────────────────────────────────────────

# Maps model name to the name of its last convolutional layer.
# EfficientNetB3 and ResNet50 end with a batch-norm'd activation before GAP;
# we use the last Conv2D-ish block output instead.
_LAST_CONV_LAYERS: Dict[str, str] = {
    "cnn":          "conv4_2",          # last Conv2D in custom CNN
    "vgg16":        "block5_conv3",     # last conv in VGG-16 backbone
    "resnet50":     "conv5_block3_out", # last residual block output
    "efficientnet": "top_activation",  # final activation before GAP in EffNetB3
}


def _find_last_conv_layer(model: tf.keras.Model, model_name: str) -> str:
    """
    Return the name of the target activation layer for Grad-CAM.

    Falls back to scanning the model for the last Conv2D layer when the
    architecture name is not in ``_LAST_CONV_LAYERS``.
    """
    if model_name in _LAST_CONV_LAYERS:
        layer_name = _LAST_CONV_LAYERS[model_name]
        # Verify it exists — walk nested sub-models too
        try:
            _get_layer_recursive(model, layer_name)
            return layer_name
        except ValueError:
            logger.warning(
                f"Layer '{layer_name}' not found in model '{model_name}', "
                "falling back to last Conv2D scan."
            )

    # Fallback: find the last layer with 4-D output (H, W, C feature map)
    last_conv = None
    for layer in model.layers:
        if isinstance(layer, (tf.keras.layers.Conv2D,
                               tf.keras.layers.DepthwiseConv2D,
                               tf.keras.layers.Activation)):
            if hasattr(layer, "output_shape"):
                shape = layer.output_shape
                if isinstance(shape, (list, tuple)) and len(shape) == 4:
                    last_conv = layer.name
    if last_conv:
        return last_conv

    raise ValueError(
        f"Cannot find a suitable convolutional layer in model '{model_name}' "
        "for Grad-CAM. Check _LAST_CONV_LAYERS."
    )


def _get_layer_recursive(model: tf.keras.Model, name: str) -> tf.keras.layers.Layer:
    """Search *model* and its sub-models for a layer by *name*."""
    for layer in model.layers:
        if layer.name == name:
            return layer
        if hasattr(layer, "layers"):
            try:
                return _get_layer_recursive(layer, name)
            except ValueError:
                pass
    raise ValueError(f"Layer '{name}' not found.")


# ─── Grad-CAM computation ─────────────────────────────────────────────────────

def _compute_gradcam_heatmap(
    model: tf.keras.Model,
    tensor: np.ndarray,
    class_index: int,
    layer_name: str,
) -> np.ndarray:
    """
    Compute a Grad-CAM heatmap using GradientTape.

    Parameters
    ----------
    model : tf.keras.Model
        Loaded Keras model.
    tensor : np.ndarray
        Preprocessed image batch (1, H, W, C).
    class_index : int
        Target class index.
    layer_name : str
        Name of the convolutional layer whose activations are used.

    Returns
    -------
    np.ndarray
        Float32 heatmap in [0, 1] with shape (H', W').
    """
    # Build a sub-model that outputs [conv_features, predictions]
    try:
        conv_layer = _get_layer_recursive(model, layer_name)
    except ValueError as exc:
        raise ValueError(f"Grad-CAM layer lookup failed: {exc}") from exc

    # For models with sub-model backbones we need to build a grad model
    # that passes through the backbone explicitly.
    grad_model = tf.keras.models.Model(
        inputs=model.inputs,
        outputs=[conv_layer.output, model.output],
    )

    # Watch the conv-layer activations
    tensor_tf = tf.cast(tensor, tf.float32)
    with tf.GradientTape() as tape:
        tape.watch(tensor_tf)
        conv_outputs, predictions = grad_model(tensor_tf, training=False)
        # Score for the target class before softmax would be ideal, but
        # post-softmax works well in practice for single-label classification.
        class_score = predictions[:, class_index]

    # Gradients of class score w.r.t. conv feature map
    grads: tf.Tensor = tape.gradient(class_score, conv_outputs)

    # Global average pooling over the spatial dimensions → (1, C)
    pooled_grads: tf.Tensor = tf.reduce_mean(grads, axis=(0, 1, 2))

    # Weight feature maps by their corresponding gradients
    conv_outputs_np: np.ndarray = conv_outputs[0].numpy()     # (H', W', C)
    pooled_grads_np: np.ndarray = pooled_grads.numpy()        # (C,)

    for i, w in enumerate(pooled_grads_np):
        conv_outputs_np[:, :, i] *= w

    # Collapse channels → heatmap (H', W')
    heatmap: np.ndarray = np.mean(conv_outputs_np, axis=-1)

    # ReLU — keep only positive influences
    heatmap = np.maximum(heatmap, 0)

    # Normalise to [0, 1]
    max_val = np.max(heatmap)
    if max_val > 0:
        heatmap /= max_val

    return heatmap.astype(np.float32)


def _overlay_heatmap(
    display_rgb: np.ndarray,
    heatmap: np.ndarray,
    alpha: float = 0.4,
) -> np.ndarray:
    """
    Resize the heatmap to match ``display_rgb`` and overlay it as a
    colour-coded (jet) transparency.

    Parameters
    ----------
    display_rgb : np.ndarray
        Original image (H, W, 3) uint8.
    heatmap : np.ndarray
        Float32 heatmap in [0, 1].
    alpha : float
        Blend factor for the overlay (0 = original, 1 = pure heatmap).

    Returns
    -------
    np.ndarray
        Blended BGR image (H, W, 3) uint8.
    """
    h, w = display_rgb.shape[:2]

    # Resize heatmap to match the display image
    heatmap_resized = cv2.resize(heatmap, (w, h))

    # Apply jet colormap: uint8 in [0, 255]
    heatmap_uint8 = np.uint8(255 * heatmap_resized)
    jet = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)  # BGR

    # Convert display image to BGR for blending
    img_bgr = cv2.cvtColor(display_rgb, cv2.COLOR_RGB2BGR)

    # Weighted overlay
    overlay = cv2.addWeighted(img_bgr, 1 - alpha, jet, alpha, 0)
    return overlay


# ─── Public entry point ───────────────────────────────────────────────────────

def generate_gradcam(
    source: str | bytes | Path,
    model_name: Optional[str] = None,
    class_index: Optional[int] = None,
    image_id: Optional[str] = None,
    *,
    alpha: float = 0.4,
) -> Dict[str, Any]:
    """
    Generate a Grad-CAM heatmap for an MRI image and save the overlay.

    Parameters
    ----------
    source : str | bytes | Path
        Image file path or raw bytes (JPEG / PNG).
    model_name : str | None
        Architecture key. Defaults to ``settings.active_model``.
    class_index : int | None
        Target class index for the heatmap. Defaults to the top-1 class
        predicted by the model (requires a forward pass).
    image_id : str | None
        Used to name the output file. A UUID is generated when *None*.
    alpha : float
        Heatmap blend factor (0–1).

    Returns
    -------
    dict
        {
          "gradcam_path": str,   # absolute path to saved overlay PNG
          "class_index":  int,
          "class_name":   str,
          "image_id":     str,
        }

    Raises
    ------
    FileNotFoundError
        When no saved weights are found.
    ValueError
        When the image cannot be decoded.
    """
    name     = (model_name or settings.active_model).lower()
    img_id   = image_id or str(uuid.uuid4())
    classes  = settings.classes

    # ── Load model ────────────────────────────────────────────────────────────
    model = load_keras_model(name)

    # ── Preprocess — get both tensor and display image ────────────────────────
    tensor, display_rgb = preprocess_image_for_gradcam(source)

    # ── Determine target class ────────────────────────────────────────────────
    if class_index is None:
        raw_preds: np.ndarray = model.predict(tensor, verbose=0)
        class_index = int(np.argmax(raw_preds[0]))

    class_name = classes[class_index] if class_index < len(classes) else str(class_index)

    # ── Find last conv layer ──────────────────────────────────────────────────
    layer_name = _find_last_conv_layer(model, name)
    logger.debug(f"Grad-CAM using layer '{layer_name}' for model '{name}'")

    # ── Compute heatmap ───────────────────────────────────────────────────────
    heatmap = _compute_gradcam_heatmap(model, tensor, class_index, layer_name)

    # ── Overlay ───────────────────────────────────────────────────────────────
    overlay_bgr = _overlay_heatmap(display_rgb, heatmap, alpha=alpha)

    # ── Save to disk ──────────────────────────────────────────────────────────
    output_dir: Path = settings.gradcam_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{img_id}.png"

    success = cv2.imwrite(str(output_path), overlay_bgr)
    if not success:
        raise IOError(f"cv2.imwrite failed — could not save Grad-CAM to {output_path}")

    logger.info(
        f"Grad-CAM saved | image_id={img_id} class={class_name} "
        f"layer={layer_name} path={output_path}"
    )

    return {
        "gradcam_path": str(output_path),
        "class_index":  class_index,
        "class_name":   class_name,
        "image_id":     img_id,
    }

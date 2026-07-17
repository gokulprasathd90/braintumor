"""
preprocess.py — Unified, context-aware image preprocessing pipeline.

This module is the single entry-point for all preprocessing in the project.
It delegates every low-level operation to the three sub-modules:

    config.py       — PreprocessConfig dataclass (all tunable parameters)
    transforms.py   — Pure stateless image functions (load, denoise, CLAHE, …)
    augmentation.py — Keras ImageDataGenerator wrappers (train only)

Five public contexts
--------------------
``preprocess_for_inference``
    Single-image path used by ``predict.py``.
    Pipeline: load → spatial (denoise + CLAHE + resize) → RGB → normalise.
    Returns float32 (1, H, W, C) batch tensor.

``preprocess_for_gradcam``
    Same spatial pipeline as inference, but also returns the pre-normalisation
    display copy (uint8 RGB) that Grad-CAM overlays onto.
    Returns (tensor, display_rgb).

``preprocess_for_preview``
    Returns the processed uint8 RGB image without normalisation so it can be
    base64-encoded and sent back to the browser for visual inspection.

``build_generators``
    Builds Keras DirectoryIterators for the **pre-split** directory layout
    produced by the dataset module:
        processed/train/<class>/   → augmented training generator
        processed/val/<class>/     → eval generator (rescale only)
    Replaces the old ``build_data_generators`` that required a single root
    directory with a validation_split fraction.

``build_test_generator``
    Builds a non-shuffled eval generator for the test split.

Backward-compatible shims
--------------------------
The old function names (``preprocess_image``, ``preprocess_image_for_gradcam``,
``build_data_generators``, ``normalize_image``, ``apply_median_filter``,
``apply_clahe``, ``resize_image``) are preserved as thin wrappers so that
the rest of the codebase (predict.py, gradcam.py, train.py, evaluate.py)
continues to work without any changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.preprocessing.config import PreprocessConfig, DEFAULT_CONFIG
from app.preprocessing.transforms import (
    apply_spatial_pipeline,
    bgr_to_rgb,
    encode_image_base64,
    load_image_bgr,
    normalize_image as _normalize,
    apply_median_filter as _median,
    apply_clahe as _clahe,
    resize_image as _resize,
)
from app.preprocessing.augmentation import (
    AugmentationConfig,
    build_data_generators_from_split,
    build_eval_datagen,
    build_train_datagen,
)


# ─────────────────────────────────────────────────────────────────────────────
# Core pipeline helper
# ─────────────────────────────────────────────────────────────────────────────

def _run_spatial_pipeline(
    source: str | bytes | Path,
    cfg: PreprocessConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load an image and run the full spatial pipeline.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (img_rgb_uint8_resized,  img_bgr_uint8_resized)
        Both are (H, W, 3) uint8 at ``cfg.image_size × cfg.image_size``.
        ``img_rgb`` is the display-ready copy; use it for Grad-CAM overlay.
    """
    img_bgr = load_image_bgr(source)                    # load from path or bytes
    img_bgr = apply_spatial_pipeline(img_bgr, cfg)      # denoise → CLAHE → resize
    img_rgb = bgr_to_rgb(img_bgr)
    return img_rgb, img_bgr


# ─────────────────────────────────────────────────────────────────────────────
# 1. Inference
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_for_inference(
    source: str | bytes | Path,
    *,
    cfg: Optional[PreprocessConfig] = None,
    expand_dims: bool = True,
) -> np.ndarray:
    """
    Full preprocessing pipeline for a single image at inference time.

    Steps
    -----
    1. Load (path or bytes).
    2. Median-filter denoise  (if ``cfg.apply_denoise``).
    3. CLAHE contrast enhance (if ``cfg.apply_clahe``).
    4. Lanczos resize to ``cfg.image_size × cfg.image_size``.
    5. BGR → RGB.
    6. z-score normalise with ``cfg.norm_mean`` / ``cfg.norm_std``.
    7. Optionally add batch dimension.

    Parameters
    ----------
    source : str | bytes | Path
        File path or raw JPEG/PNG bytes.
    cfg : PreprocessConfig | None
        Pipeline config.  Uses ``DEFAULT_CONFIG`` when None.
    expand_dims : bool
        If True returns shape (1, H, W, C); if False returns (H, W, C).

    Returns
    -------
    np.ndarray
        float32 tensor ready for ``model.predict()``.

    Raises
    ------
    ValueError
        When the image cannot be decoded.
    """
    cfg = cfg or DEFAULT_CONFIG
    img_rgb, _ = _run_spatial_pipeline(source, cfg)

    arr: np.ndarray
    if cfg.normalise:
        arr = _normalize(img_rgb, mean=cfg.norm_mean, std=cfg.norm_std)
    else:
        arr = img_rgb.astype(np.float32) / 255.0

    if expand_dims:
        arr = np.expand_dims(arr, axis=0)

    logger.debug(f"preprocess_for_inference → shape={arr.shape} dtype={arr.dtype}")
    return arr


# ─────────────────────────────────────────────────────────────────────────────
# 2. Grad-CAM
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_for_gradcam(
    source: str | bytes | Path,
    *,
    cfg: Optional[PreprocessConfig] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Preprocessing for Grad-CAM — returns the model tensor AND the display image.

    The display image is used to overlay the Grad-CAM heatmap; it must be
    uint8 RGB at the same spatial resolution as the model input.

    Parameters
    ----------
    source : str | bytes | Path
        File path or raw JPEG/PNG bytes.
    cfg : PreprocessConfig | None
        Pipeline config.  Uses ``DEFAULT_CONFIG`` when None.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        tensor      — float32 (1, H, W, C) normalised, for ``model.predict()``.
        display_rgb — uint8  (H, W, C) RGB, for heatmap overlay.
    """
    cfg = cfg or DEFAULT_CONFIG
    img_rgb, _ = _run_spatial_pipeline(source, cfg)

    # Keep a uint8 copy *before* normalisation for the overlay
    display_rgb: np.ndarray = img_rgb.copy()

    if cfg.normalise:
        arr = _normalize(img_rgb, mean=cfg.norm_mean, std=cfg.norm_std)
    else:
        arr = img_rgb.astype(np.float32) / 255.0

    tensor = np.expand_dims(arr, axis=0)

    logger.debug(
        f"preprocess_for_gradcam → tensor={tensor.shape} display={display_rgb.shape}"
    )
    return tensor, display_rgb


# ─────────────────────────────────────────────────────────────────────────────
# 3. Preview (no normalisation — returns displayable uint8 RGB)
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_for_preview(
    source: str | bytes | Path,
    *,
    cfg: Optional[PreprocessConfig] = None,
) -> np.ndarray:
    """
    Run the spatial pipeline and return a display-ready uint8 RGB image.

    No normalisation is applied so the result can be base64-encoded and
    sent back to the browser as-is.

    Parameters
    ----------
    source : str | bytes | Path
        File path or raw JPEG/PNG bytes.
    cfg : PreprocessConfig | None
        Pipeline config.

    Returns
    -------
    np.ndarray
        uint8 RGB (H, W, 3) at ``cfg.image_size × cfg.image_size``.
    """
    cfg = cfg or DEFAULT_CONFIG
    img_rgb, _ = _run_spatial_pipeline(source, cfg)
    return img_rgb


# ─────────────────────────────────────────────────────────────────────────────
# 4. Training / validation generators (pre-split directories)
# ─────────────────────────────────────────────────────────────────────────────

def build_generators(
    processed_dir: str | Path,
    *,
    batch_size: int = 32,
    cfg: Optional[PreprocessConfig] = None,
    aug_cfg: Optional[AugmentationConfig] = None,
    seed: int = 42,
):
    """
    Build (train_gen, val_gen) from a **pre-split** processed directory.

    Expected layout (produced by ``app.dataset.splitter``)::

        processed_dir/
            train/ <class folders>
            val/   <class folders>
            test/  <class folders>

    The training generator applies the full ``AugmentationConfig`` stack.
    The validation generator rescales only — no augmentation.

    Parameters
    ----------
    processed_dir : str | Path
        Root of the processed dataset.
    batch_size : int
        Mini-batch size.
    cfg : PreprocessConfig | None
        Pipeline config (used for ``image_size``).
    aug_cfg : AugmentationConfig | None
        Augmentation parameters for the training split.
    seed : int
        Random seed.

    Returns
    -------
    tuple[DirectoryIterator, DirectoryIterator]
        (train_generator, val_generator)
    """
    cfg = cfg or DEFAULT_CONFIG
    processed_dir = Path(processed_dir)
    train_dir = processed_dir / "train"
    val_dir   = processed_dir / "val"

    return build_data_generators_from_split(
        train_dir=train_dir,
        val_dir=val_dir,
        image_size=cfg.image_size,
        batch_size=batch_size,
        aug_cfg=aug_cfg,
        seed=seed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Test generator
# ─────────────────────────────────────────────────────────────────────────────

def build_test_generator(
    test_dir: str | Path,
    *,
    cfg: Optional[PreprocessConfig] = None,
    target_size: Optional[int] = None,
    batch_size: int = 32,
):
    """
    Build a non-shuffled test generator for evaluation.

    Accepts either:
    - A pre-split ``processed_dir/test/`` directory (preferred), or
    - Any directory containing one sub-folder per class.

    No augmentation — only rescaling to [0, 1].

    Parameters
    ----------
    test_dir : str | Path
        Root directory with one sub-folder per class.
    cfg : PreprocessConfig | None
        Pipeline config (used for image_size if target_size is None).
    target_size : int | None
        Explicit resize override (legacy kwarg — prefer cfg).
    batch_size : int
        Batch size.

    Returns
    -------
    DirectoryIterator
    """
    cfg = cfg or DEFAULT_CONFIG
    size = target_size or cfg.image_size
    test_dir = Path(test_dir)

    if not test_dir.exists():
        raise FileNotFoundError(f"Test directory not found: {test_dir}")

    datagen = build_eval_datagen()
    gen = datagen.flow_from_directory(
        str(test_dir),
        target_size=(size, size),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=False,
    )

    logger.info(
        f"Test generator built | samples={gen.samples} "
        f"batch={batch_size} size={size}"
    )
    return gen


# ─────────────────────────────────────────────────────────────────────────────
# Backward-compatible shims
# ─────────────────────────────────────────────────────────────────────────────
# These thin wrappers keep the existing callers (predict.py, gradcam.py,
# train.py, evaluate.py) working without modification.

def preprocess_image(
    source: str | bytes | Path,
    *,
    target_size: Optional[int] = None,
    apply_denoise: bool = True,
    apply_contrast: bool = True,
    expand_dims: bool = True,
    cfg: Optional[PreprocessConfig] = None,
) -> np.ndarray:
    """
    Backward-compatible shim → ``preprocess_for_inference()``.

    The ``target_size``, ``apply_denoise``, and ``apply_contrast`` keyword
    arguments are converted into a ``PreprocessConfig`` override so that
    callers with the old signature continue to work.
    """
    _cfg = PreprocessConfig(
        image_size=target_size or (cfg.image_size if cfg else DEFAULT_CONFIG.image_size),
        apply_denoise=apply_denoise,
        apply_clahe=apply_contrast,
        # carry all other fields from the supplied cfg or default
        normalise=cfg.normalise if cfg else DEFAULT_CONFIG.normalise,
        norm_mean=cfg.norm_mean if cfg else DEFAULT_CONFIG.norm_mean,
        norm_std=cfg.norm_std   if cfg else DEFAULT_CONFIG.norm_std,
        clahe_clip_limit=cfg.clahe_clip_limit if cfg else DEFAULT_CONFIG.clahe_clip_limit,
        clahe_tile_grid_size=cfg.clahe_tile_grid_size if cfg else DEFAULT_CONFIG.clahe_tile_grid_size,
        denoise_kernel_size=cfg.denoise_kernel_size if cfg else DEFAULT_CONFIG.denoise_kernel_size,
    )
    return preprocess_for_inference(source, cfg=_cfg, expand_dims=expand_dims)


def preprocess_image_for_gradcam(
    source: str | bytes | Path,
    *,
    target_size: Optional[int] = None,
    apply_denoise: bool = True,
    apply_contrast: bool = True,
    cfg: Optional[PreprocessConfig] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Backward-compatible shim → ``preprocess_for_gradcam()``."""
    _cfg = PreprocessConfig(
        image_size=target_size or (cfg.image_size if cfg else DEFAULT_CONFIG.image_size),
        apply_denoise=apply_denoise,
        apply_clahe=apply_contrast,
        normalise=cfg.normalise if cfg else DEFAULT_CONFIG.normalise,
        norm_mean=cfg.norm_mean if cfg else DEFAULT_CONFIG.norm_mean,
        norm_std=cfg.norm_std   if cfg else DEFAULT_CONFIG.norm_std,
        clahe_clip_limit=cfg.clahe_clip_limit if cfg else DEFAULT_CONFIG.clahe_clip_limit,
        clahe_tile_grid_size=cfg.clahe_tile_grid_size if cfg else DEFAULT_CONFIG.clahe_tile_grid_size,
        denoise_kernel_size=cfg.denoise_kernel_size if cfg else DEFAULT_CONFIG.denoise_kernel_size,
    )
    return preprocess_for_gradcam(source, cfg=_cfg)


def build_data_generators(
    dataset_dir: str | Path,
    *,
    target_size: Optional[int] = None,
    batch_size: int = 32,
    validation_split: float = 0.2,
    seed: int = 42,
):
    """
    Backward-compatible shim for the old single-directory generator.

    .. deprecated::
        Prefer ``build_generators(processed_dir)`` which uses the pre-split
        layout produced by ``app.dataset.splitter``.

    When the old layout is used (one root dir, no train/val sub-dirs) this
    shim falls back to Keras ``validation_split`` behaviour.
    """
    dataset_dir = Path(dataset_dir)
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    size = target_size or settings.image_size

    # Detect whether this is already a split directory
    train_dir = dataset_dir / "train"
    val_dir   = dataset_dir / "val"
    if train_dir.is_dir() and val_dir.is_dir():
        return build_data_generators_from_split(
            train_dir=train_dir,
            val_dir=val_dir,
            image_size=size,
            batch_size=batch_size,
            seed=seed,
        )

    # Legacy: single-directory with validation_split
    logger.warning(
        "build_data_generators() called with a single root directory and "
        "validation_split. Prefer build_generators(processed_dir) with a "
        "pre-split layout."
    )
    train_datagen = build_train_datagen()
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    val_datagen = ImageDataGenerator(
        rescale=1.0 / 255.0,
        validation_split=validation_split,
    )
    train_datagen_split = build_train_datagen(validation_split=validation_split)

    train_gen = train_datagen_split.flow_from_directory(
        str(dataset_dir),
        target_size=(size, size),
        batch_size=batch_size,
        class_mode="categorical",
        subset="training",
        seed=seed,
        shuffle=True,
    )
    val_gen = val_datagen.flow_from_directory(
        str(dataset_dir),
        target_size=(size, size),
        batch_size=batch_size,
        class_mode="categorical",
        subset="validation",
        seed=seed,
        shuffle=False,
    )

    logger.info(
        f"Data generators built (legacy) | train={train_gen.samples} "
        f"val={val_gen.samples} batch={batch_size} size={size}"
    )
    return train_gen, val_gen


# ── Low-level re-exports (kept in this namespace for old imports) ─────────────
def apply_median_filter(img: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Re-export — see transforms.apply_median_filter."""
    return _median(img, kernel_size)


def apply_clahe(img_bgr: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    """Re-export — see transforms.apply_clahe."""
    return _clahe(img_bgr, clip_limit)


def resize_image(img: np.ndarray, size: int) -> np.ndarray:
    """Re-export — see transforms.resize_image."""
    return _resize(img, size)


def normalize_image(img: np.ndarray) -> np.ndarray:
    """Re-export — see transforms.normalize_image (uses DEFAULT_CONFIG means/stds)."""
    return _normalize(
        img,
        mean=DEFAULT_CONFIG.norm_mean,
        std=DEFAULT_CONFIG.norm_std,
    )

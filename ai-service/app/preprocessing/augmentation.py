"""
augmentation.py — Advanced data augmentation for the training split only.

Augmentation is deliberately kept out of the validation, test, inference,
and Grad-CAM pipelines.  This module provides:

1. ``AugmentationConfig``   — typed dataclass controlling every augmentation
                              parameter (all values default to values tuned
                              for MRI brain-tumour data).
2. ``build_train_datagen()`` — returns a Keras ``ImageDataGenerator`` with
                               the full augmentation stack wired in.
3. ``build_eval_datagen()``  — returns a minimal generator (rescale only)
                               for validation, test, and any evaluation context.
4. ``apply_augmentation()``  — apply the augmentation stack to a single numpy
                               image for offline preview / debugging.

Why these augmentations for MRI?
---------------------------------
- Rotation (±15°)       Scanners may acquire at slightly different head angles.
- Width/height shift    Minor patient head positioning variation.
- Zoom (±10%)           Slight focal length and scan-plane differences.
- Horizontal flip       Left/right symmetry of the brain is medically valid.
- Shear (±0.05)         Small geometric distortions from scanner geometry.
- Brightness (±15%)     MRI signal intensity can vary across acquisition protocols.
- NO vertical flip      Brain orientation is physically meaningful (superior/inferior).
- NO channel shuffle    MRI is grayscale-derived; colour channels carry the same signal.

Usage
-----
    from app.preprocessing.augmentation import AugmentationConfig, build_train_datagen

    aug_cfg = AugmentationConfig(rotation_range=20)
    train_gen = build_train_datagen(aug_cfg)
    gen = train_gen.flow_from_directory(train_dir, ...)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from app.core.logging import logger


@dataclass
class AugmentationConfig:
    """
    Configures the Keras ImageDataGenerator augmentation pipeline.

    All parameters map directly to ``ImageDataGenerator`` kwargs.
    Set a parameter to 0 / False to disable that augmentation.

    Parameters
    ----------
    rotation_range : float
        Degrees of random rotation [0, 180].
    width_shift_range : float
        Fraction of total width for horizontal shift.
    height_shift_range : float
        Fraction of total height for vertical shift.
    shear_range : float
        Shear angle in counter-clockwise direction as radians.
    zoom_range : float | tuple
        Range for random zoom. If float, [1-zoom, 1+zoom]. Use a tuple for
        asymmetric zoom.
    horizontal_flip : bool
        Randomly flip images horizontally.
    vertical_flip : bool
        Randomly flip images vertically. Should be False for MRI.
    brightness_range : tuple[float, float] | None
        Range for random brightness adjustment as multiplicative factors.
        ``None`` disables brightness augmentation.
    fill_mode : str
        How to fill newly created pixels: 'nearest' | 'constant' | 'reflect' | 'wrap'.
    cval : float
        Constant fill value when fill_mode='constant'.
    featurewise_center : bool
        Set input mean to 0 over the dataset.
    featurewise_std_normalization : bool
        Divide inputs by std of the dataset.
    """

    rotation_range:        float = 15.0
    width_shift_range:     float = 0.08
    height_shift_range:    float = 0.08
    shear_range:           float = 0.05
    zoom_range:            float = 0.10
    horizontal_flip:       bool  = True
    vertical_flip:         bool  = False   # must stay False for MRI anatomy
    brightness_range:      Optional[Tuple[float, float]] = (0.85, 1.15)
    fill_mode:             str   = "nearest"
    cval:                  float = 0.0
    featurewise_center:    bool  = False
    featurewise_std_normalization: bool = False

    def to_dict(self) -> dict:
        d = {
            "rotation_range":     self.rotation_range,
            "width_shift_range":  self.width_shift_range,
            "height_shift_range": self.height_shift_range,
            "shear_range":        self.shear_range,
            "zoom_range":         self.zoom_range,
            "horizontal_flip":    self.horizontal_flip,
            "vertical_flip":      self.vertical_flip,
            "brightness_range":   list(self.brightness_range) if self.brightness_range else None,
            "fill_mode":          self.fill_mode,
        }
        return d


# ── Module-level defaults ──────────────────────────────────────────────────────
DEFAULT_AUG_CONFIG = AugmentationConfig()


def build_train_datagen(
    aug_cfg: Optional[AugmentationConfig] = None,
    validation_split: float = 0.0,
) -> ImageDataGenerator:
    """
    Build a Keras ``ImageDataGenerator`` with the full augmentation stack.

    Parameters
    ----------
    aug_cfg : AugmentationConfig | None
        Augmentation parameters. Defaults to ``DEFAULT_AUG_CONFIG``.
    validation_split : float
        Fraction of data to reserve for validation when using
        ``flow_from_directory`` with ``subset='training'``.
        Pass 0.0 when using pre-split train/val directories.

    Returns
    -------
    ImageDataGenerator
        Ready to use with ``flow_from_directory``.
    """
    cfg = aug_cfg or DEFAULT_AUG_CONFIG

    kwargs = dict(
        rescale=1.0 / 255.0,
        rotation_range=cfg.rotation_range,
        width_shift_range=cfg.width_shift_range,
        height_shift_range=cfg.height_shift_range,
        shear_range=cfg.shear_range,
        zoom_range=cfg.zoom_range,
        horizontal_flip=cfg.horizontal_flip,
        vertical_flip=cfg.vertical_flip,
        fill_mode=cfg.fill_mode,
        cval=cfg.cval,
        featurewise_center=cfg.featurewise_center,
        featurewise_std_normalization=cfg.featurewise_std_normalization,
    )

    if cfg.brightness_range is not None:
        kwargs["brightness_range"] = list(cfg.brightness_range)

    if validation_split > 0:
        kwargs["validation_split"] = validation_split

    logger.debug(f"Training datagen built | aug_params={cfg.to_dict()}")
    return ImageDataGenerator(**kwargs)


def build_eval_datagen(validation_split: float = 0.0) -> ImageDataGenerator:
    """
    Build a Keras ``ImageDataGenerator`` for evaluation contexts.

    No augmentation — only rescaling to [0, 1].

    Parameters
    ----------
    validation_split : float
        Passed to ``ImageDataGenerator`` when using a single directory
        with a val subset. Pass 0.0 for pre-split directories.

    Returns
    -------
    ImageDataGenerator
    """
    kwargs: dict = {"rescale": 1.0 / 255.0}
    if validation_split > 0:
        kwargs["validation_split"] = validation_split
    return ImageDataGenerator(**kwargs)


def build_data_generators_from_split(
    train_dir: str | Path,
    val_dir: str | Path,
    *,
    image_size: int = 224,
    batch_size: int = 32,
    aug_cfg: Optional[AugmentationConfig] = None,
    seed: int = 42,
):
    """
    Build (train_gen, val_gen) from **pre-split** directories.

    This is the preferred approach when ``dataset/processed/train/`` and
    ``dataset/processed/val/`` have already been created by the splitter.
    Each directory must contain one sub-folder per class.

    Parameters
    ----------
    train_dir : str | Path
        Directory containing class sub-folders for training.
    val_dir : str | Path
        Directory containing class sub-folders for validation.
    image_size : int
        Target (height, width) in pixels.
    batch_size : int
        Mini-batch size.
    aug_cfg : AugmentationConfig | None
        Augmentation config for training. Defaults to ``DEFAULT_AUG_CONFIG``.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    tuple[DirectoryIterator, DirectoryIterator]
        (train_generator, val_generator)
    """
    train_dir = Path(train_dir)
    val_dir   = Path(val_dir)

    if not train_dir.exists():
        raise FileNotFoundError(f"Training directory not found: {train_dir}")
    if not val_dir.exists():
        raise FileNotFoundError(f"Validation directory not found: {val_dir}")

    train_datagen = build_train_datagen(aug_cfg)
    val_datagen   = build_eval_datagen()

    train_gen = train_datagen.flow_from_directory(
        str(train_dir),
        target_size=(image_size, image_size),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=True,
        seed=seed,
    )

    val_gen = val_datagen.flow_from_directory(
        str(val_dir),
        target_size=(image_size, image_size),
        batch_size=batch_size,
        class_mode="categorical",
        shuffle=False,
    )

    logger.info(
        f"Split generators built | "
        f"train={train_gen.samples} val={val_gen.samples} "
        f"batch={batch_size} size={image_size}"
    )
    return train_gen, val_gen


def apply_augmentation(
    img_rgb: np.ndarray,
    aug_cfg: Optional[AugmentationConfig] = None,
    seed: int = 42,
    n_samples: int = 1,
) -> list[np.ndarray]:
    """
    Apply augmentation to a single RGB uint8 image and return *n_samples* variants.

    Useful for offline preview/debugging and for generating augmented
    previews via the API.

    Parameters
    ----------
    img_rgb : np.ndarray
        RGB uint8 image (H, W, 3).
    aug_cfg : AugmentationConfig | None
        Augmentation parameters.
    seed : int
        Random seed.
    n_samples : int
        Number of augmented variants to return.

    Returns
    -------
    list[np.ndarray]
        List of *n_samples* RGB uint8 augmented images.
    """
    cfg       = aug_cfg or DEFAULT_AUG_CONFIG
    datagen   = build_train_datagen(cfg)

    # ImageDataGenerator.flow expects (N, H, W, C) float32
    img_f32  = img_rgb.astype(np.float32)           # keep [0, 255] range here
    batch    = np.expand_dims(img_f32, axis=0)       # (1, H, W, C)

    np.random.seed(seed)
    results: list[np.ndarray] = []
    gen = datagen.flow(batch, batch_size=1, shuffle=False)

    for _ in range(n_samples):
        aug_batch = next(gen)                         # (1, H, W, C) float32 [0,1]
        aug_img   = (aug_batch[0] * 255.0).clip(0, 255).astype(np.uint8)
        results.append(aug_img)

    return results

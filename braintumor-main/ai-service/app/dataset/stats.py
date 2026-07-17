"""
stats.py — Dataset statistics computation.

Computes per-class and global statistics over a dataset directory,
including image counts, class balance, pixel-level intensity statistics
(mean / std per channel), and spatial dimension distribution.

Two modes
---------
fast (default)   Count images only — runs in milliseconds.
full             Also sample pixel statistics — reads a subset of images
                 with OpenCV.  Used for normalisation constant verification.

Usage
-----
    from app.dataset.stats import compute_dataset_stats
    stats = compute_dataset_stats("/data/dataset/raw")
    print(stats["class_distribution"])
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.dataset.validator import VALID_IMAGE_EXTENSIONS


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _collect_class_images(dataset_dir: Path, classes: List[str]) -> Dict[str, List[Path]]:
    """Return {class_name: [image_path, ...]} for all discovered images."""
    result: Dict[str, List[Path]] = {}
    for cls in classes:
        cls_dir = dataset_dir / cls
        if not cls_dir.is_dir():
            result[cls] = []
            continue
        result[cls] = sorted(
            p for p in cls_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTENSIONS
        )
    return result


def _sample_pixel_stats(
    image_paths: List[Path],
    max_samples: int,
    seed: int,
) -> Dict[str, Any]:
    """
    Read a random subset of images and compute channel-wise mean and std.

    Returns
    -------
    dict
        {
          "mean_rgb": [r_mean, g_mean, b_mean],
          "std_rgb":  [r_std,  g_std,  b_std],
          "samples_used": int,
          "failed_reads": int,
        }
    """
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(image_paths), size=min(max_samples, len(image_paths)), replace=False)
    sampled = [image_paths[i] for i in indices]

    channel_sums   = np.zeros(3, dtype=np.float64)
    channel_sq_sums = np.zeros(3, dtype=np.float64)
    pixel_count = 0
    failed = 0

    for path in sampled:
        img_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img_bgr is None:
            failed += 1
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float64) / 255.0
        h, w, _ = img_rgb.shape
        n = h * w
        channel_sums    += img_rgb.reshape(-1, 3).sum(axis=0)
        channel_sq_sums += (img_rgb.reshape(-1, 3) ** 2).sum(axis=0)
        pixel_count += n

    if pixel_count == 0:
        return {"mean_rgb": [0, 0, 0], "std_rgb": [0, 0, 0],
                "samples_used": 0, "failed_reads": failed}

    mean = channel_sums / pixel_count
    variance = (channel_sq_sums / pixel_count) - (mean ** 2)
    std = np.sqrt(np.maximum(variance, 0.0))

    return {
        "mean_rgb":    [round(float(v), 6) for v in mean],
        "std_rgb":     [round(float(v), 6) for v in std],
        "samples_used": len(sampled) - failed,
        "failed_reads": failed,
    }


def _sample_dimensions(
    image_paths: List[Path],
    max_samples: int,
    seed: int,
) -> Dict[str, Any]:
    """
    Read a subset of images and collect (height, width) pairs.

    Returns min, max, and most common dimension as a summary.
    """
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(image_paths), size=min(max_samples, len(image_paths)), replace=False)
    sampled = [image_paths[i] for i in indices]

    heights, widths = [], []
    for path in sampled:
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        heights.append(h)
        widths.append(w)

    if not heights:
        return {}

    return {
        "height_min":  int(min(heights)),
        "height_max":  int(max(heights)),
        "height_mean": round(float(np.mean(heights)), 1),
        "width_min":   int(min(widths)),
        "width_max":   int(max(widths)),
        "width_mean":  round(float(np.mean(widths)), 1),
        "all_same_size": len(set(zip(heights, widths))) == 1,
    }


# ─── Public API ───────────────────────────────────────────────────────────────

def compute_dataset_stats(
    dataset_dir: str | Path,
    *,
    classes: Optional[List[str]] = None,
    full: bool = False,
    pixel_sample_size: int = 500,
    dimension_sample_size: int = 200,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Compute statistics for a dataset directory.

    Parameters
    ----------
    dataset_dir : str | Path
        Root directory (one sub-folder per class).
    classes : list[str] | None
        Which class folders to inspect. Defaults to ``settings.classes``.
    full : bool
        If True, also read image pixels to compute channel mean/std and
        spatial dimension distribution.
    pixel_sample_size : int
        Max images to read for pixel statistics (``full=True`` only).
    dimension_sample_size : int
        Max images to read for dimension statistics (``full=True`` only).
    seed : int
        Random seed for reproducible sampling.

    Returns
    -------
    dict
        {
          "dataset_dir":         str,
          "classes":             [str, ...],
          "class_counts":        {cls: int, ...},
          "total_images":        int,
          "class_distribution":  {cls: float, ...},   # fraction 0–1
          "class_weights":       {cls: float, ...},   # inverse freq for loss
          "imbalance_ratio":     float,               # max_count / min_count
          "is_balanced":         bool,                # imbalance_ratio < 2.0
          # only present when full=True:
          "pixel_stats":         {"mean_rgb": [...], "std_rgb": [...], ...},
          "dimension_stats":     {"height_min": int, ...},
        }
    """
    dataset_dir = Path(dataset_dir)
    cls_list    = classes or settings.classes

    logger.info(f"Computing dataset statistics | dir={dataset_dir} full={full}")

    # ── Count images per class ────────────────────────────────────────────────
    class_images = _collect_class_images(dataset_dir, cls_list)
    class_counts = {cls: len(imgs) for cls, imgs in class_images.items()}
    total        = sum(class_counts.values())

    # ── Distribution and balance ──────────────────────────────────────────────
    class_distribution: Dict[str, float] = {}
    class_weights:      Dict[str, float] = {}

    if total > 0:
        for cls, cnt in class_counts.items():
            frac = cnt / total
            class_distribution[cls] = round(frac, 4)
            # Inverse frequency weight (normalised so mean weight = 1)
            class_weights[cls] = round((total / (len(cls_list) * cnt)) if cnt > 0 else 0.0, 4)

    counts_nonzero = [c for c in class_counts.values() if c > 0]
    imbalance_ratio = (
        round(max(counts_nonzero) / min(counts_nonzero), 3)
        if len(counts_nonzero) >= 2
        else 1.0
    )
    is_balanced = imbalance_ratio < 2.0

    stats: Dict[str, Any] = {
        "dataset_dir":        str(dataset_dir),
        "classes":            cls_list,
        "class_counts":       class_counts,
        "total_images":       total,
        "class_distribution": class_distribution,
        "class_weights":      class_weights,
        "imbalance_ratio":    imbalance_ratio,
        "is_balanced":        is_balanced,
    }

    # ── Full pixel + dimension stats ──────────────────────────────────────────
    if full and total > 0:
        all_images = [img for imgs in class_images.values() for img in imgs]

        logger.info(
            f"Sampling pixel statistics from {min(pixel_sample_size, len(all_images))} images..."
        )
        stats["pixel_stats"] = _sample_pixel_stats(all_images, pixel_sample_size, seed)

        logger.info(
            f"Sampling dimension statistics from {min(dimension_sample_size, len(all_images))} images..."
        )
        stats["dimension_stats"] = _sample_dimensions(all_images, dimension_sample_size, seed)

    logger.info(
        f"Stats complete | total={total} classes={cls_list} "
        f"imbalance={imbalance_ratio:.2f} balanced={is_balanced}"
    )
    return stats


def compute_split_stats(
    processed_dir: str | Path,
    *,
    classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compute image counts for each split inside *processed_dir*.

    Expected layout::

        processed_dir/
            train/ <class folders>
            val/   <class folders>
            test/  <class folders>

    Returns
    -------
    dict
        {
          "processed_dir": str,
          "splits": {
            "train": {"glioma": int, ...},
            "val":   {...},
            "test":  {...},
          },
          "totals": {"train": int, "val": int, "test": int},
          "grand_total": int,
        }
    """
    processed_dir = Path(processed_dir)
    cls_list      = classes or settings.classes

    splits: Dict[str, Dict[str, int]] = {}
    totals: Dict[str, int] = {}

    for split in ("train", "val", "test"):
        split_dir = processed_dir / split
        if not split_dir.is_dir():
            splits[split] = {cls: 0 for cls in cls_list}
            totals[split] = 0
            continue

        counts = {}
        for cls in cls_list:
            cls_dir = split_dir / cls
            if not cls_dir.is_dir():
                counts[cls] = 0
            else:
                counts[cls] = sum(
                    1 for p in cls_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTENSIONS
                )
        splits[split] = counts
        totals[split] = sum(counts.values())

    return {
        "processed_dir": str(processed_dir),
        "splits":        splits,
        "totals":        totals,
        "grand_total":   sum(totals.values()),
    }

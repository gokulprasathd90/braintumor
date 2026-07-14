"""
app/dataset — Dataset management package.

The top-level ``prepare_dataset()`` orchestrator runs the full pipeline:
  1. Validate raw dataset structure        (validator.py)
  2. Compute raw statistics                (stats.py)
  3. Split into train / val / test         (splitter.py)
  4. Compute split statistics              (stats.py)
  5. Save dataset_info.json sidecar        (metadata.py)

Public API re-exported here so callers only need one import:

    from app.dataset import prepare_dataset, validate_dataset, load_dataset_info
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import logger

from app.dataset.validator import validate_dataset, ValidationResult
from app.dataset.splitter  import split_dataset,   SplitResult
from app.dataset.stats     import compute_dataset_stats, compute_split_stats
from app.dataset.metadata  import (
    save_dataset_info,
    load_dataset_info,
    update_dataset_info,
    dataset_info_exists,
)

__all__ = [
    # Orchestrator
    "prepare_dataset",
    # Sub-module public functions
    "validate_dataset",
    "split_dataset",
    "compute_dataset_stats",
    "compute_split_stats",
    "save_dataset_info",
    "load_dataset_info",
    "update_dataset_info",
    "dataset_info_exists",
    # Result types
    "ValidationResult",
    "SplitResult",
]


def prepare_dataset(
    raw_dir: Optional[str | Path] = None,
    output_dir: Optional[str | Path] = None,
    *,
    train_ratio: float = 0.70,
    val_ratio:   float = 0.15,
    test_ratio:  float = 0.15,
    seed: int = 42,
    overwrite: bool = False,
    full_stats: bool = False,
    pixel_sample_size: int = 500,
    classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run the complete dataset preparation pipeline.

    Steps
    -----
    1. Validate the raw dataset directory.
    2. Compute raw-split statistics (fast mode by default).
    3. Perform stratified train / val / test split onto disk.
    4. Compute post-split statistics for verification.
    5. Write ``dataset_info.json`` into the processed directory.

    Parameters
    ----------
    raw_dir : str | Path | None
        Source dataset root (one sub-folder per class).
        Defaults to ``settings.dataset_raw_dir``.
    output_dir : str | Path | None
        Destination root for the split dataset.
        Defaults to ``settings.dataset_processed_dir``.
    train_ratio : float
        Fraction of each class assigned to training (default 0.70).
    val_ratio : float
        Fraction assigned to validation (default 0.15).
    test_ratio : float
        Fraction assigned to test (default 0.15).
    seed : int
        Random seed — guarantees reproducible splits.
    overwrite : bool
        Wipe and recreate the output directory if it already exists.
    full_stats : bool
        If True, sample pixel mean / std and dimension stats (slower).
    pixel_sample_size : int
        Max images to read for pixel statistics (``full_stats=True`` only).
    classes : list[str] | None
        Class names to include. Defaults to ``settings.classes``.

    Returns
    -------
    dict
        {
          "validation":    ValidationResult.to_dict(),
          "raw_stats":     dict,
          "split":         SplitResult.to_dict(),
          "split_stats":   dict,
          "metadata_path": str,
          "duration_s":    float,
        }

    Raises
    ------
    ValueError
        When the raw dataset fails validation.
    FileExistsError
        When *output_dir* is non-empty and *overwrite* is False.
    """
    t0         = time.perf_counter()
    raw_dir    = Path(raw_dir)    if raw_dir    else settings.dataset_raw_dir
    output_dir = Path(output_dir) if output_dir else settings.dataset_processed_dir
    cls_list   = classes or settings.classes

    logger.info(
        f"prepare_dataset started | raw={raw_dir} out={output_dir} "
        f"split={train_ratio}/{val_ratio}/{test_ratio} seed={seed}"
    )

    # ── Step 1: Validate ──────────────────────────────────────────────────────
    logger.info("Step 1/5 — Validating raw dataset...")
    validation = validate_dataset(
        raw_dir,
        expected_classes=cls_list,
        require_all_classes=True,
    )
    if not validation.is_valid:
        raise ValueError(
            "Dataset validation failed:\n"
            + "\n".join(f"  • {e}" for e in validation.errors)
        )

    # ── Step 2: Raw statistics ────────────────────────────────────────────────
    logger.info("Step 2/5 — Computing raw dataset statistics...")
    raw_stats = compute_dataset_stats(
        raw_dir,
        classes=cls_list,
        full=full_stats,
        pixel_sample_size=pixel_sample_size,
        seed=seed,
    )

    # ── Step 3: Split ─────────────────────────────────────────────────────────
    logger.info("Step 3/5 — Splitting dataset...")
    split_result = split_dataset(
        raw_dir,
        output_dir,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
        overwrite=overwrite,
        classes=cls_list,
    )

    # ── Step 4: Post-split statistics ─────────────────────────────────────────
    logger.info("Step 4/5 — Verifying split counts...")
    split_stats = compute_split_stats(output_dir, classes=cls_list)

    # ── Step 5: Save metadata ─────────────────────────────────────────────────
    logger.info("Step 5/5 — Writing dataset_info.json...")
    metadata_path = save_dataset_info(
        output_dir,
        raw_dir=raw_dir,
        classes=cls_list,
        split_ratios=split_result.ratios_used,
        split_counts=split_result.split_counts,
        total_per_split=split_result.total_per_split,
        raw_class_counts=raw_stats["class_counts"],
        class_weights=raw_stats["class_weights"],
        imbalance_ratio=raw_stats["imbalance_ratio"],
        is_balanced=raw_stats["is_balanced"],
        seed=seed,
        pixel_stats=raw_stats.get("pixel_stats"),
    )

    duration_s = round(time.perf_counter() - t0, 2)

    logger.info(
        f"prepare_dataset complete | "
        f"train={split_result.total_per_split['train']} "
        f"val={split_result.total_per_split['val']} "
        f"test={split_result.total_per_split['test']} "
        f"duration={duration_s}s"
    )

    return {
        "validation":    validation.to_dict(),
        "raw_stats":     raw_stats,
        "split":         split_result.to_dict(),
        "split_stats":   split_stats,
        "metadata_path": str(metadata_path),
        "duration_s":    duration_s,
    }

"""
splitter.py — Stratified train / validation / test split.

Copies (or symlinks) images from the raw dataset into the processed
directory maintaining the Keras sub-folder layout:

    processed/
        train/
            glioma/   meningioma/   notumor/   pituitary/
        val/
            glioma/   ...
        test/
            glioma/   ...

Stratified split ensures each class is represented proportionally in
every split.  A fixed random seed guarantees reproducibility.

Usage
-----
    from app.dataset.splitter import split_dataset
    result = split_dataset(
        raw_dir="/data/dataset/raw",
        output_dir="/data/dataset/processed",
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
    )
"""

from __future__ import annotations

import random
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.dataset.validator import validate_dataset, VALID_IMAGE_EXTENSIONS

# Split names written to disk
SPLIT_NAMES = ("train", "val", "test")


@dataclass
class SplitResult:
    """Structured result returned by ``split_dataset()``."""

    output_dir: str
    split_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # e.g. {"train": {"glioma": 800, ...}, "val": {...}, "test": {...}}
    total_per_split: Dict[str, int] = field(default_factory=dict)
    ratios_used: Dict[str, float] = field(default_factory=dict)
    seed: int = 42
    classes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "output_dir":      self.output_dir,
            "split_counts":    self.split_counts,
            "total_per_split": self.total_per_split,
            "ratios_used":     self.ratios_used,
            "seed":            self.seed,
            "classes":         self.classes,
        }


def _collect_images(class_dir: Path) -> List[Path]:
    """Return a sorted list of valid image files in *class_dir*."""
    return sorted(
        p for p in class_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTENSIONS
    )


def _split_indices(
    n: int,
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> Tuple[List[int], List[int], List[int]]:
    """
    Split *n* item indices into (train, val, test) lists.

    The test set gets whatever is left after train + val so that rounding
    errors never lose images.
    """
    indices = list(range(n))
    rng = random.Random(seed)
    rng.shuffle(indices)

    n_train = int(n * train_ratio)
    n_val   = int(n * val_ratio)

    train_idx = indices[:n_train]
    val_idx   = indices[n_train:n_train + n_val]
    test_idx  = indices[n_train + n_val:]

    return train_idx, val_idx, test_idx


def split_dataset(
    raw_dir: str | Path,
    output_dir: Optional[str | Path] = None,
    *,
    train_ratio: float = 0.70,
    val_ratio:   float = 0.15,
    test_ratio:  float = 0.15,
    seed: int = 42,
    overwrite: bool = False,
    copy_files: bool = True,
    classes: Optional[List[str]] = None,
) -> SplitResult:
    """
    Split a raw dataset into stratified train / val / test sets on disk.

    Parameters
    ----------
    raw_dir : str | Path
        Root of the raw dataset (one sub-folder per class).
    output_dir : str | Path | None
        Destination root. Defaults to ``settings.dataset_processed_dir``.
    train_ratio : float
        Fraction of each class assigned to the training split.
    val_ratio : float
        Fraction assigned to validation.
    test_ratio : float
        Fraction assigned to test (remainder after train + val).
    seed : int
        Random seed for reproducibility.
    overwrite : bool
        If True, wipe the existing output directory before writing.
        If False, raise ``FileExistsError`` when the output already exists.
    copy_files : bool
        If True, physically copy images. If False, create symbolic links
        (faster and saves disk space — not supported on Windows).
    classes : list[str] | None
        Classes to include. Defaults to ``settings.classes``.

    Returns
    -------
    SplitResult

    Raises
    ------
    ValueError
        When ratios do not sum to approximately 1.0, or when validation
        fails (missing directories, too few images).
    FileExistsError
        When the output directory already exists and *overwrite* is False.
    """
    raw_dir    = Path(raw_dir)
    output_dir = Path(output_dir) if output_dir else settings.dataset_processed_dir
    cls_list   = classes or settings.classes

    # ── Validate ratios ───────────────────────────────────────────────────────
    ratio_sum = train_ratio + val_ratio + test_ratio
    if abs(ratio_sum - 1.0) > 1e-6:
        raise ValueError(
            f"train_ratio + val_ratio + test_ratio must equal 1.0, got {ratio_sum:.4f}"
        )
    if any(r <= 0 for r in (train_ratio, val_ratio, test_ratio)):
        raise ValueError("All split ratios must be > 0.")

    # ── Validate source dataset ───────────────────────────────────────────────
    validation = validate_dataset(
        raw_dir,
        expected_classes=cls_list,
        min_images_per_class=10,
        require_all_classes=True,
    )
    if not validation.is_valid:
        raise ValueError(
            f"Source dataset failed validation:\n"
            + "\n".join(f"  • {e}" for e in validation.errors)
        )

    # ── Output directory ──────────────────────────────────────────────────────
    if output_dir.exists() and any(output_dir.iterdir()):
        if overwrite:
            logger.warning(f"Overwriting existing split at {output_dir}")
            shutil.rmtree(output_dir)
        else:
            raise FileExistsError(
                f"Output directory '{output_dir}' already exists and is non-empty. "
                "Pass overwrite=True to replace it."
            )

    # Create split sub-directories
    for split in SPLIT_NAMES:
        for cls in cls_list:
            (output_dir / split / cls).mkdir(parents=True, exist_ok=True)

    # ── Perform split per class ────────────────────────────────────────────────
    split_counts: Dict[str, Dict[str, int]] = {s: {} for s in SPLIT_NAMES}

    for cls in cls_list:
        cls_dir = raw_dir / cls
        images  = _collect_images(cls_dir)
        n       = len(images)

        train_idx, val_idx, test_idx = _split_indices(n, train_ratio, val_ratio, seed)

        buckets: Dict[str, List[int]] = {
            "train": train_idx,
            "val":   val_idx,
            "test":  test_idx,
        }

        for split_name, idxs in buckets.items():
            dest_dir = output_dir / split_name / cls
            split_counts[split_name][cls] = len(idxs)

            for idx in idxs:
                src  = images[idx]
                dest = dest_dir / src.name

                if copy_files:
                    shutil.copy2(src, dest)
                else:
                    # Symlink — use absolute path so links survive relocation
                    if dest.exists() or dest.is_symlink():
                        dest.unlink()
                    dest.symlink_to(src.resolve())

        logger.debug(
            f"Split class '{cls}' | n={n} "
            f"train={len(train_idx)} val={len(val_idx)} test={len(test_idx)}"
        )

    total_per_split = {
        split: sum(split_counts[split].values())
        for split in SPLIT_NAMES
    }

    result = SplitResult(
        output_dir=str(output_dir),
        split_counts=split_counts,
        total_per_split=total_per_split,
        ratios_used={
            "train": train_ratio,
            "val":   val_ratio,
            "test":  test_ratio,
        },
        seed=seed,
        classes=cls_list,
    )

    logger.info(
        f"Dataset split complete | "
        f"train={total_per_split['train']} "
        f"val={total_per_split['val']} "
        f"test={total_per_split['test']} "
        f"→ {output_dir}"
    )
    return result

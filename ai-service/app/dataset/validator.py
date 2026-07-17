"""
validator.py — Raw dataset structure validation.

Checks that a candidate dataset directory matches the expected Keras
directory layout before any splitting or training begins:

    <dataset_root>/
        glioma/          ← one folder per class
            img001.jpg
            ...
        meningioma/
        notumor/
        pituitary/

Validation rules
----------------
1. The root directory exists and is not empty.
2. At least one sub-directory that matches the configured class names exists.
3. Every configured class has at least ``min_images_per_class`` images.
4. All files inside class directories are valid image extensions.
5. Each class directory contains no nested sub-directories (flat layout).
6. No duplicate filenames across classes (warns, not fatal).

Usage
-----
    from app.dataset.validator import validate_dataset
    result = validate_dataset("/data/dataset/raw")
    if not result.is_valid:
        print(result.errors)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.core.config import settings
from app.core.logging import logger

# Accepted image file extensions (lowercase)
VALID_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

# Minimum images required per class to consider the dataset usable
DEFAULT_MIN_IMAGES_PER_CLASS = 10


@dataclass
class ValidationResult:
    """Structured result returned by ``validate_dataset()``."""

    is_valid: bool
    dataset_dir: str
    classes_found: List[str] = field(default_factory=list)
    classes_missing: List[str] = field(default_factory=list)
    class_counts: Dict[str, int] = field(default_factory=dict)
    total_images: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_valid":        self.is_valid,
            "dataset_dir":     self.dataset_dir,
            "classes_found":   self.classes_found,
            "classes_missing": self.classes_missing,
            "class_counts":    self.class_counts,
            "total_images":    self.total_images,
            "errors":          self.errors,
            "warnings":        self.warnings,
        }


def _is_image_file(path: Path) -> bool:
    """Return True if *path* has a recognised image extension."""
    return path.suffix.lower() in VALID_IMAGE_EXTENSIONS


def validate_dataset(
    dataset_dir: str | Path,
    *,
    expected_classes: Optional[List[str]] = None,
    min_images_per_class: int = DEFAULT_MIN_IMAGES_PER_CLASS,
    require_all_classes: bool = True,
) -> ValidationResult:
    """
    Validate the raw dataset directory structure.

    Parameters
    ----------
    dataset_dir : str | Path
        Root directory to validate.
    expected_classes : list[str] | None
        Class names that must be present. Defaults to ``settings.classes``.
    min_images_per_class : int
        Minimum number of valid image files each class folder must contain.
    require_all_classes : bool
        If True, missing configured classes are reported as errors (not just
        warnings). Set False to allow partial datasets during development.

    Returns
    -------
    ValidationResult
        ``is_valid`` is True only when there are zero errors.
    """
    dataset_dir  = Path(dataset_dir)
    exp_classes  = expected_classes or settings.classes
    errors:   List[str] = []
    warnings: List[str] = []

    # ── Rule 1: root directory exists ─────────────────────────────────────────
    if not dataset_dir.exists():
        return ValidationResult(
            is_valid=False,
            dataset_dir=str(dataset_dir),
            errors=[f"Dataset directory does not exist: {dataset_dir}"],
        )

    if not dataset_dir.is_dir():
        return ValidationResult(
            is_valid=False,
            dataset_dir=str(dataset_dir),
            errors=[f"Path is not a directory: {dataset_dir}"],
        )

    # ── Discover sub-directories ──────────────────────────────────────────────
    subdirs = [p for p in dataset_dir.iterdir() if p.is_dir()]

    if not subdirs:
        return ValidationResult(
            is_valid=False,
            dataset_dir=str(dataset_dir),
            errors=["Dataset directory contains no sub-directories (expected one per class)."],
        )

    found_class_dirs = {p.name: p for p in subdirs}

    # ── Rule 2: configured classes present ────────────────────────────────────
    classes_found:   List[str] = []
    classes_missing: List[str] = []

    for cls in exp_classes:
        if cls in found_class_dirs:
            classes_found.append(cls)
        else:
            classes_missing.append(cls)
            msg = f"Expected class directory '{cls}' not found in {dataset_dir}"
            if require_all_classes:
                errors.append(msg)
            else:
                warnings.append(msg)

    # Warn about extra directories that are not in the config
    extra_dirs = set(found_class_dirs.keys()) - set(exp_classes)
    for extra in sorted(extra_dirs):
        warnings.append(
            f"Extra directory '{extra}' is not in the configured class list "
            f"({exp_classes}) — it will be ignored during training."
        )

    # ── Rule 3–5: per-class image validation ──────────────────────────────────
    class_counts: Dict[str, int] = {}
    all_filenames: List[str] = []

    for cls in classes_found:
        cls_dir = found_class_dirs[cls]
        all_entries = list(cls_dir.iterdir())

        # Rule 5: no nested sub-directories
        nested = [e for e in all_entries if e.is_dir()]
        if nested:
            warnings.append(
                f"Class '{cls}' contains {len(nested)} sub-director(ies) "
                f"({[n.name for n in nested[:3]]}…). "
                "Only flat image directories are supported."
            )

        # Collect valid image files
        image_files = [e for e in all_entries if e.is_file() and _is_image_file(e)]
        non_image   = [e for e in all_entries if e.is_file() and not _is_image_file(e)]

        if non_image:
            warnings.append(
                f"Class '{cls}' contains {len(non_image)} non-image file(s) "
                f"(e.g. {non_image[0].name}) — they will be ignored."
            )

        count = len(image_files)
        class_counts[cls] = count

        # Rule 3: minimum image count
        if count < min_images_per_class:
            errors.append(
                f"Class '{cls}' has only {count} image(s) "
                f"(minimum required: {min_images_per_class})."
            )

        all_filenames.extend(f.name for f in image_files)

    # Rule 6: duplicate filenames across classes
    seen: Dict[str, int] = {}
    for fname in all_filenames:
        seen[fname] = seen.get(fname, 0) + 1
    duplicates = [fname for fname, cnt in seen.items() if cnt > 1]
    if duplicates:
        warnings.append(
            f"Found {len(duplicates)} filename(s) that appear in more than "
            f"one class directory (e.g. {duplicates[:3]}). "
            "This may cause issues with some data loaders."
        )

    total_images = sum(class_counts.values())
    is_valid     = len(errors) == 0

    result = ValidationResult(
        is_valid=is_valid,
        dataset_dir=str(dataset_dir),
        classes_found=classes_found,
        classes_missing=classes_missing,
        class_counts=class_counts,
        total_images=total_images,
        errors=errors,
        warnings=warnings,
    )

    # ── Log summary ───────────────────────────────────────────────────────────
    status = "VALID" if is_valid else "INVALID"
    logger.info(
        f"Dataset validation [{status}] | dir={dataset_dir} "
        f"classes={classes_found} total={total_images} "
        f"errors={len(errors)} warnings={len(warnings)}"
    )
    for err  in errors:   logger.error(f"  [DATASET] {err}")
    for warn in warnings: logger.warning(f"  [DATASET] {warn}")

    return result

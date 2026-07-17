"""
metadata.py — Dataset metadata persistence (dataset_info.json).

Saves a structured JSON sidecar file alongside the processed dataset so
that training, evaluation, and the API can query dataset provenance,
class indices, and split counts without re-scanning the file system.

File location:  <processed_dir>/dataset_info.json

Schema
------
{
  "schema_version":    "1.0",
  "created_at":        "<ISO-8601>",
  "updated_at":        "<ISO-8601>",
  "raw_dir":           str,
  "processed_dir":     str,
  "classes":           [str, ...],
  "class_to_index":    {class_name: int, ...},
  "index_to_class":    {int: class_name, ...},
  "split_ratios":      {"train": float, "val": float, "test": float},
  "split_counts":      {"train": {cls: int}, "val": {...}, "test": {...}},
  "total_per_split":   {"train": int, "val": int, "test": int},
  "total_images":      int,
  "raw_class_counts":  {cls: int, ...},
  "class_weights":     {cls: float, ...},
  "imbalance_ratio":   float,
  "is_balanced":       bool,
  "seed":              int,
  "image_size":        int,
  "image_channels":    int,
  "pixel_stats":       {...} | null,
}

Usage
-----
    from app.dataset.metadata import save_dataset_info, load_dataset_info
    save_dataset_info(processed_dir, split_result, stats)
    info = load_dataset_info(processed_dir)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import logger

METADATA_FILENAME = "dataset_info.json"
SCHEMA_VERSION    = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_dataset_info(
    processed_dir: str | Path,
    *,
    raw_dir: str | Path,
    classes: list,
    split_ratios: Dict[str, float],
    split_counts: Dict[str, Dict[str, int]],
    total_per_split: Dict[str, int],
    raw_class_counts: Dict[str, int],
    class_weights: Dict[str, float],
    imbalance_ratio: float,
    is_balanced: bool,
    seed: int = 42,
    pixel_stats: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Write ``dataset_info.json`` into *processed_dir*.

    Parameters
    ----------
    processed_dir : str | Path
        Root of the processed (split) dataset.
    raw_dir : str | Path
        Source directory the split was built from.
    classes : list[str]
        Ordered class name list (index = model output index).
    split_ratios : dict
        {"train": float, "val": float, "test": float}
    split_counts : dict
        {"train": {cls: int, ...}, "val": ..., "test": ...}
    total_per_split : dict
        {"train": int, "val": int, "test": int}
    raw_class_counts : dict
        Image count per class in the *raw* dataset.
    class_weights : dict
        Inverse-frequency weights for handling class imbalance.
    imbalance_ratio : float
        max_class_count / min_class_count.
    is_balanced : bool
        True when imbalance_ratio < 2.0.
    seed : int
        Random seed used for splitting.
    pixel_stats : dict | None
        Channel-wise mean / std (populated by ``stats.compute_dataset_stats``
        with ``full=True``).
    extra : dict | None
        Any additional key/value pairs to include in the JSON.

    Returns
    -------
    Path
        Absolute path to the written JSON file.
    """
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    out_path = processed_dir / METADATA_FILENAME

    # Build class index maps
    class_to_index = {cls: i for i, cls in enumerate(classes)}
    index_to_class = {str(i): cls for i, cls in enumerate(classes)}

    total_images = sum(total_per_split.values())

    info: Dict[str, Any] = {
        "schema_version":   SCHEMA_VERSION,
        "created_at":       _now_iso(),
        "updated_at":       _now_iso(),
        "raw_dir":          str(raw_dir),
        "processed_dir":    str(processed_dir),
        "classes":          list(classes),
        "class_to_index":   class_to_index,
        "index_to_class":   index_to_class,
        "split_ratios":     split_ratios,
        "split_counts":     split_counts,
        "total_per_split":  total_per_split,
        "total_images":     total_images,
        "raw_class_counts": raw_class_counts,
        "class_weights":    class_weights,
        "imbalance_ratio":  imbalance_ratio,
        "is_balanced":      is_balanced,
        "seed":             seed,
        "image_size":       settings.image_size,
        "image_channels":   settings.image_channels,
        "pixel_stats":      pixel_stats,
    }

    if extra:
        info.update(extra)

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)

    logger.info(f"Dataset metadata saved → {out_path}")
    return out_path


def load_dataset_info(
    processed_dir: str | Path,
) -> Optional[Dict[str, Any]]:
    """
    Load ``dataset_info.json`` from *processed_dir*.

    Parameters
    ----------
    processed_dir : str | Path
        Root of the processed dataset.

    Returns
    -------
    dict | None
        Parsed JSON dict, or None if the file does not exist.
    """
    info_path = Path(processed_dir) / METADATA_FILENAME

    if not info_path.exists():
        logger.debug(f"No dataset_info.json found at {info_path}")
        return None

    try:
        with open(info_path, "r", encoding="utf-8") as fh:
            info = json.load(fh)
        logger.debug(f"Loaded dataset metadata from {info_path}")
        return info
    except Exception as exc:
        logger.warning(f"Failed to load dataset_info.json from {info_path}: {exc}")
        return None


def update_dataset_info(
    processed_dir: str | Path,
    updates: Dict[str, Any],
) -> Optional[Path]:
    """
    Merge *updates* into an existing ``dataset_info.json`` and re-write it.

    Returns the path to the updated file, or None if no existing file was found.
    """
    existing = load_dataset_info(processed_dir)
    if existing is None:
        logger.warning(
            f"Cannot update dataset_info.json — file not found in {processed_dir}"
        )
        return None

    existing.update(updates)
    existing["updated_at"] = _now_iso()

    out_path = Path(processed_dir) / METADATA_FILENAME
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2)

    logger.info(f"Dataset metadata updated → {out_path}")
    return out_path


def dataset_info_exists(processed_dir: str | Path) -> bool:
    """Return True if ``dataset_info.json`` exists in *processed_dir*."""
    return (Path(processed_dir) / METADATA_FILENAME).exists()

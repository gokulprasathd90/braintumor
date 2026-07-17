"""
quality.py — Image quality validation before training or inference.

Checks that an uploaded or dataset image meets minimum quality thresholds
before it enters the preprocessing pipeline.  All checks are fast (a few
milliseconds per image) and operate on the raw decoded image array.

Quality dimensions checked
--------------------------
1. Decodability   — the file must decode to a valid numpy array.
2. Dimensions     — minimum width × height.
3. File size      — maximum raw bytes (configurable).
4. Colour mode    — must be convertible to RGB with 3 channels.
5. Intensity      — mean pixel value must be within [min_mean, max_mean]
                    (catches pure-black / pure-white / blank scans).
6. Sharpness      — Laplacian variance above a blur threshold
                    (catches heavily blurred or out-of-focus scans).
7. Saturation     — checks for completely flat / zero-variance images.

Usage
-----
    from app.preprocessing.quality import validate_image_quality
    report = validate_image_quality(image_bytes)
    if not report.is_valid:
        raise ValueError(report.summary())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

from app.preprocessing.config import PreprocessConfig, DEFAULT_CONFIG


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class QualityCheck:
    """Result of a single quality dimension check."""
    name:    str
    passed:  bool
    value:   Optional[float] = None   # measured value (if numeric)
    threshold: Optional[float] = None  # threshold used
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "name":      self.name,
            "passed":    self.passed,
            "value":     round(self.value, 4) if self.value is not None else None,
            "threshold": self.threshold,
            "message":   self.message,
        }


@dataclass
class ImageQualityReport:
    """
    Aggregated quality report for a single image.

    Attributes
    ----------
    is_valid : bool
        True only when all checks pass (no failures; warnings are allowed).
    checks : list[QualityCheck]
        Per-dimension results.
    image_width : int
        Decoded image width in pixels.
    image_height : int
        Decoded image height in pixels.
    file_size_bytes : int
        Size of the raw source bytes.
    warnings : list[str]
        Non-fatal quality notes (image is still usable).
    errors : list[str]
        Fatal quality failures (image should not be used).
    """
    is_valid: bool
    checks: List[QualityCheck] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    file_size_bytes: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [f"{'VALID' if self.is_valid else 'INVALID'} image quality report"]
        parts.append(f"  Size: {self.image_width}×{self.image_height} px")
        for chk in self.checks:
            status = "✓" if chk.passed else "✗"
            parts.append(f"  {status} {chk.name}: {chk.message}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "is_valid":        self.is_valid,
            "image_width":     self.image_width,
            "image_height":    self.image_height,
            "file_size_bytes": self.file_size_bytes,
            "checks":          [c.to_dict() for c in self.checks],
            "warnings":        self.warnings,
            "errors":          self.errors,
        }


# ─── Individual check functions ───────────────────────────────────────────────

def _check_dimensions(
    img: np.ndarray, cfg: PreprocessConfig
) -> QualityCheck:
    h, w = img.shape[:2]
    passed = w >= cfg.min_width and h >= cfg.min_height
    msg = (
        f"{w}×{h} px — OK"
        if passed
        else f"{w}×{h} px is below minimum {cfg.min_width}×{cfg.min_height} px"
    )
    return QualityCheck(
        name="dimensions", passed=passed,
        value=min(w, h), threshold=float(min(cfg.min_width, cfg.min_height)),
        message=msg,
    )


def _check_channels(img: np.ndarray) -> QualityCheck:
    c = img.shape[2] if img.ndim == 3 else 1
    passed = c in (1, 3)
    msg = f"{c} channel(s) — {'OK' if passed else 'unsupported channel count'}"
    return QualityCheck(name="channels", passed=passed, value=float(c), message=msg)


def _check_file_size(size_bytes: int, cfg: PreprocessConfig) -> QualityCheck:
    if cfg.max_file_size_bytes <= 0:
        return QualityCheck(name="file_size", passed=True,
                            value=float(size_bytes), message="no limit configured")
    passed = size_bytes <= cfg.max_file_size_bytes
    mb = size_bytes / (1024 * 1024)
    limit_mb = cfg.max_file_size_bytes / (1024 * 1024)
    msg = (
        f"{mb:.2f} MB — OK"
        if passed
        else f"{mb:.2f} MB exceeds limit of {limit_mb:.1f} MB"
    )
    return QualityCheck(
        name="file_size", passed=passed,
        value=float(size_bytes), threshold=float(cfg.max_file_size_bytes),
        message=msg,
    )


def _check_mean_intensity(img_bgr: np.ndarray, cfg: PreprocessConfig) -> QualityCheck:
    """Detect near-black or near-white (blank) images."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean_val = float(np.mean(gray))
    passed = cfg.min_mean_intensity <= mean_val <= cfg.max_mean_intensity
    msg = (
        f"mean={mean_val:.1f} — OK"
        if passed
        else (
            f"mean={mean_val:.1f} is {'too dark' if mean_val < cfg.min_mean_intensity else 'too bright'} "
            f"(expected [{cfg.min_mean_intensity}, {cfg.max_mean_intensity}])"
        )
    )
    return QualityCheck(
        name="mean_intensity", passed=passed,
        value=mean_val,
        threshold=cfg.min_mean_intensity if mean_val < cfg.min_mean_intensity else cfg.max_mean_intensity,
        message=msg,
    )


def _check_sharpness(img_bgr: np.ndarray, cfg: PreprocessConfig) -> QualityCheck:
    """
    Blur detection via Laplacian variance.

    The variance of the Laplacian is a standard focus measure: higher values
    indicate a sharper image.  MRI images with very low variance are likely
    artefacts or extremely blurred.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    passed = laplacian_var >= cfg.min_laplacian_variance
    msg = (
        f"laplacian_var={laplacian_var:.2f} — OK"
        if passed
        else f"laplacian_var={laplacian_var:.2f} below threshold {cfg.min_laplacian_variance} (too blurry)"
    )
    return QualityCheck(
        name="sharpness", passed=passed,
        value=laplacian_var, threshold=cfg.min_laplacian_variance,
        message=msg,
    )


def _check_pixel_variance(img_bgr: np.ndarray) -> QualityCheck:
    """Detect completely flat images (zero standard deviation across all pixels)."""
    std_val = float(np.std(img_bgr.astype(np.float32)))
    passed  = std_val > 0.5
    msg = (
        f"pixel_std={std_val:.3f} — OK"
        if passed
        else f"pixel_std={std_val:.3f} — image appears completely uniform (possible artefact)"
    )
    return QualityCheck(name="pixel_variance", passed=passed, value=std_val, message=msg)


# ─── Public validator ─────────────────────────────────────────────────────────

def validate_image_quality(
    source: str | bytes | Path,
    cfg: Optional[PreprocessConfig] = None,
) -> ImageQualityReport:
    """
    Run all quality checks on an image and return a structured report.

    Parameters
    ----------
    source : str | bytes | Path
        File path or raw image bytes (JPEG / PNG).
    cfg : PreprocessConfig | None
        Quality thresholds to use. Defaults to ``DEFAULT_CONFIG``.

    Returns
    -------
    ImageQualityReport
        ``is_valid`` is True when all checks pass.
        Individual check details available in ``checks``.
    """
    from app.preprocessing.transforms import load_image_bgr

    cfg = cfg or DEFAULT_CONFIG
    checks: List[QualityCheck] = []
    errors: List[str] = []
    warnings: List[str] = []

    # ── Determine raw size ────────────────────────────────────────────────────
    if isinstance(source, (str, Path)):
        try:
            file_size = Path(source).stat().st_size
        except OSError:
            file_size = 0
    else:
        file_size = len(source)

    # ── File-size check (before decode) ──────────────────────────────────────
    size_check = _check_file_size(file_size, cfg)
    checks.append(size_check)
    if not size_check.passed:
        errors.append(size_check.message)

    # ── Decode ────────────────────────────────────────────────────────────────
    try:
        img_bgr = load_image_bgr(source)
    except ValueError as exc:
        errors.append(f"Decode failed: {exc}")
        return ImageQualityReport(
            is_valid=False,
            checks=checks,
            file_size_bytes=file_size,
            errors=errors,
        )

    h, w = img_bgr.shape[:2]

    # ── Dimension check ───────────────────────────────────────────────────────
    dim_check = _check_dimensions(img_bgr, cfg)
    checks.append(dim_check)
    if not dim_check.passed:
        errors.append(dim_check.message)

    # ── Channel check ─────────────────────────────────────────────────────────
    ch_check = _check_channels(img_bgr)
    checks.append(ch_check)
    if not ch_check.passed:
        errors.append(ch_check.message)

    # ── Intensity check ───────────────────────────────────────────────────────
    intensity_check = _check_mean_intensity(img_bgr, cfg)
    checks.append(intensity_check)
    if not intensity_check.passed:
        errors.append(intensity_check.message)

    # ── Sharpness check ───────────────────────────────────────────────────────
    sharpness_check = _check_sharpness(img_bgr, cfg)
    checks.append(sharpness_check)
    if not sharpness_check.passed:
        # Blurry images are warnings, not hard errors — MRI can legitimately be soft
        warnings.append(sharpness_check.message)

    # ── Pixel variance check ──────────────────────────────────────────────────
    var_check = _check_pixel_variance(img_bgr)
    checks.append(var_check)
    if not var_check.passed:
        errors.append(var_check.message)

    is_valid = len(errors) == 0

    return ImageQualityReport(
        is_valid=is_valid,
        checks=checks,
        image_width=w,
        image_height=h,
        file_size_bytes=file_size,
        warnings=warnings,
        errors=errors,
    )


def validate_batch_quality(
    paths: List[str | Path],
    cfg: Optional[PreprocessConfig] = None,
    *,
    fail_fast: bool = False,
) -> Dict[str, ImageQualityReport]:
    """
    Run quality checks on a list of image paths.

    Parameters
    ----------
    paths : list[str | Path]
        Image file paths to validate.
    cfg : PreprocessConfig | None
        Shared config for all checks.
    fail_fast : bool
        If True, raise ``ValueError`` on the first failed image.

    Returns
    -------
    dict[str, ImageQualityReport]
        Keyed by file path string.
    """
    results: Dict[str, ImageQualityReport] = {}
    for path in paths:
        report = validate_image_quality(path, cfg)
        results[str(path)] = report
        if fail_fast and not report.is_valid:
            raise ValueError(
                f"Image quality check failed for '{path}':\n{report.summary()}"
            )
    return results

"""
transforms.py — Pure stateless image transform functions.

Every function here:
  - Takes a numpy array in and returns a numpy array out.
  - Has no side effects (no logging, no I/O, no global state).
  - Is independently testable.

These are the building blocks consumed by preprocess.py and augmentation.py.

Colour-space convention
-----------------------
OpenCV functions operate on BGR.  All public functions that accept a "raw"
image from disk expect BGR.  Functions that produce an RGB output say so
explicitly in their docstring.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from app.preprocessing.config import PreprocessConfig


# ─── I/O ─────────────────────────────────────────────────────────────────────

def load_image_bgr(source: str | bytes | Path) -> np.ndarray:
    """
    Load an image from a file path or raw bytes and return a BGR uint8 array.

    Parameters
    ----------
    source : str | bytes | Path
        File path or encoded bytes (JPEG / PNG).

    Returns
    -------
    np.ndarray
        BGR uint8 image (H, W, 3).

    Raises
    ------
    ValueError
        When the image cannot be decoded.
    """
    if isinstance(source, (str, Path)):
        img = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Failed to load image from path: {source}")
        return img

    arr = np.frombuffer(source, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image bytes — not a valid JPEG or PNG.")
    return img


def encode_image_png(img_rgb: np.ndarray) -> bytes:
    """
    Encode an RGB uint8 image as PNG bytes.

    Parameters
    ----------
    img_rgb : np.ndarray
        RGB uint8 image (H, W, 3).

    Returns
    -------
    bytes
        PNG-encoded bytes.
    """
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    success, buf = cv2.imencode(".png", img_bgr)
    if not success:
        raise RuntimeError("cv2.imencode failed while encoding preview PNG.")
    return buf.tobytes()


def encode_image_base64(img_rgb: np.ndarray) -> str:
    """Return a base64-encoded PNG string (data URI ready)."""
    png_bytes = encode_image_png(img_rgb)
    return base64.b64encode(png_bytes).decode("ascii")


# ─── Denoising ────────────────────────────────────────────────────────────────

def apply_median_filter(img: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """
    Reduce salt-and-pepper noise with a median filter.

    Parameters
    ----------
    img : np.ndarray
        BGR or RGB uint8 image (H, W, C).
    kernel_size : int
        Odd kernel size (3 or 5 recommended for MRI).

    Returns
    -------
    np.ndarray
        Denoised uint8 image, same shape as input.
    """
    if kernel_size % 2 == 0:
        raise ValueError(f"kernel_size must be odd, got {kernel_size}.")
    return cv2.medianBlur(img, kernel_size)


def apply_gaussian_blur(img: np.ndarray, kernel_size: int = 3, sigma: float = 0) -> np.ndarray:
    """
    Apply Gaussian blur (smooth noise, preserve edges less aggressively than median).

    Parameters
    ----------
    img : np.ndarray
        BGR or RGB uint8 image.
    kernel_size : int
        Odd kernel size.
    sigma : float
        Gaussian standard deviation (0 = auto-compute from kernel size).
    """
    if kernel_size % 2 == 0:
        raise ValueError(f"kernel_size must be odd, got {kernel_size}.")
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigma)


# ─── Contrast enhancement ─────────────────────────────────────────────────────

def apply_clahe(
    img_bgr: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Contrast Limited Adaptive Histogram Equalisation on the L-channel.

    Improves local contrast in MRI images without over-amplifying noise.

    Parameters
    ----------
    img_bgr : np.ndarray
        BGR uint8 image.
    clip_limit : float
        CLAHE clip limit.
    tile_grid_size : tuple[int, int]
        Tile grid size.

    Returns
    -------
    np.ndarray
        Contrast-enhanced BGR uint8 image.
    """
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l_eq = clahe.apply(l_channel)
    lab_eq = cv2.merge([l_eq, a, b])
    return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)


def apply_histogram_equalisation(img_bgr: np.ndarray) -> np.ndarray:
    """
    Global histogram equalisation on the L-channel (cruder than CLAHE,
    useful as a baseline comparison).

    Parameters
    ----------
    img_bgr : np.ndarray
        BGR uint8 image.

    Returns
    -------
    np.ndarray
        Equalised BGR uint8 image.
    """
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    l_eq = cv2.equalizeHist(l_channel)
    return cv2.cvtColor(cv2.merge([l_eq, a, b]), cv2.COLOR_LAB2BGR)


# ─── Spatial ──────────────────────────────────────────────────────────────────

def resize_image(img: np.ndarray, size: int) -> np.ndarray:
    """
    Resize to ``size × size`` using Lanczos interpolation.

    Lanczos is preferred over bilinear/bicubic for downscaling because it
    minimises aliasing artefacts in high-frequency MRI texture.

    Parameters
    ----------
    img : np.ndarray
        Any uint8 image (H, W, C).
    size : int
        Target side length in pixels.

    Returns
    -------
    np.ndarray
        Resized uint8 image of shape (size, size, C).
    """
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}.")
    return cv2.resize(img, (size, size), interpolation=cv2.INTER_LANCZOS4)


def pad_to_square(img: np.ndarray, fill_value: int = 0) -> np.ndarray:
    """
    Pad a non-square image with ``fill_value`` so that H == W before resizing.

    This avoids aspect-ratio distortion for rectangular MRI scans.

    Parameters
    ----------
    img : np.ndarray
        uint8 image (H, W, C).
    fill_value : int
        Padding pixel value [0, 255].

    Returns
    -------
    np.ndarray
        Square uint8 image of shape (max(H,W), max(H,W), C).
    """
    h, w = img.shape[:2]
    if h == w:
        return img

    side = max(h, w)
    c = img.shape[2] if img.ndim == 3 else 1
    canvas = np.full((side, side, c) if img.ndim == 3 else (side, side),
                     fill_value, dtype=img.dtype)
    y_off = (side - h) // 2
    x_off = (side - w) // 2
    canvas[y_off: y_off + h, x_off: x_off + w] = img
    return canvas


# ─── Colour conversion ────────────────────────────────────────────────────────

def bgr_to_rgb(img_bgr: np.ndarray) -> np.ndarray:
    """Convert BGR uint8 → RGB uint8."""
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def rgb_to_bgr(img_rgb: np.ndarray) -> np.ndarray:
    """Convert RGB uint8 → BGR uint8."""
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


# ─── Normalisation ────────────────────────────────────────────────────────────

def normalize_image(
    img_rgb: np.ndarray,
    mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
    std:  Tuple[float, float, float] = (0.229, 0.224, 0.225),
) -> np.ndarray:
    """
    Rescale uint8 [0, 255] → float32 [0, 1] then apply per-channel z-score.

    Parameters
    ----------
    img_rgb : np.ndarray
        RGB uint8 image (H, W, 3).
    mean : tuple[float, float, float]
        Per-channel mean (RGB order).
    std : tuple[float, float, float]
        Per-channel standard deviation (RGB order).

    Returns
    -------
    np.ndarray
        Float32 array of shape (H, W, 3).
    """
    arr = img_rgb.astype(np.float32) / 255.0
    _mean = np.array(mean, dtype=np.float32)
    _std  = np.array(std,  dtype=np.float32)
    return (arr - _mean) / _std


def rescale_only(img_rgb: np.ndarray) -> np.ndarray:
    """
    Rescale uint8 [0, 255] → float32 [0, 1] without z-score normalisation.

    Used by Keras ImageDataGenerator (which handles its own rescaling) and
    for preview rendering.
    """
    return img_rgb.astype(np.float32) / 255.0


def denormalize_image(
    arr: np.ndarray,
    mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
    std:  Tuple[float, float, float] = (0.229, 0.224, 0.225),
) -> np.ndarray:
    """
    Reverse z-score normalisation → uint8 RGB for display.

    Parameters
    ----------
    arr : np.ndarray
        Float32 normalised image (H, W, 3).
    mean, std : tuple
        Same values used for normalisation.

    Returns
    -------
    np.ndarray
        uint8 RGB image (H, W, 3) clipped to [0, 255].
    """
    _mean = np.array(mean, dtype=np.float32)
    _std  = np.array(std,  dtype=np.float32)
    recovered = (arr * _std + _mean) * 255.0
    return np.clip(recovered, 0, 255).astype(np.uint8)


# ─── Combined per-config helpers ──────────────────────────────────────────────

def apply_spatial_pipeline(img_bgr: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    """
    Apply the full spatial pipeline (denoise → CLAHE → resize) from *cfg*.

    Operates entirely in BGR space. Does NOT normalise.

    Parameters
    ----------
    img_bgr : np.ndarray
        BGR uint8 input image.
    cfg : PreprocessConfig
        Pipeline configuration.

    Returns
    -------
    np.ndarray
        BGR uint8 image of shape (cfg.image_size, cfg.image_size, 3).
    """
    if cfg.apply_denoise:
        img_bgr = apply_median_filter(img_bgr, cfg.denoise_kernel_size)

    if cfg.apply_clahe:
        img_bgr = apply_clahe(img_bgr, cfg.clahe_clip_limit, cfg.clahe_tile_grid_size)

    img_bgr = resize_image(img_bgr, cfg.image_size)
    return img_bgr

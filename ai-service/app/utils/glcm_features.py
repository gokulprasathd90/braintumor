"""
glcm_features.py — Real GLCM texture feature extraction using scikit-image.

Extracts all 7 features described in the paper (Eq. 8–14):
  Entropy, Correlation, Energy, Contrast, Mean, Std Dev, Variance

Steps
-----
1. Load image → grayscale
2. Resize to 256×256 (consistent with preprocessing)
3. Quantize to 8 gray levels (reduces GLCM to 8×8, faster + more stable)
4. Build GLCM at 4 directions (0°, 45°, 90°, 135°), distance=1
5. Average properties across directions
6. Compute Entropy separately (not in graycoprops)

Usage
-----
    from app.utils.glcm_features import extract_glcm_features
    features = extract_glcm_features(image_bytes_or_path)
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops

# Paper uses 8 gray levels — matches a compact 8×8 GLCM
GRAY_LEVELS = 8
DISTANCES   = [1]
ANGLES      = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]  # 0°, 45°, 90°, 135°
IMG_SIZE    = 256   # resize before GLCM for consistency


def _load_gray(source: Union[str, bytes, Path]) -> np.ndarray:
    """Load image as uint8 grayscale."""
    if isinstance(source, (str, Path)):
        img = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Cannot read image: {source}")
        return img
    arr = np.frombuffer(source, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Cannot decode image bytes")
    return img


def extract_glcm_features(source: Union[str, bytes, Path]) -> dict:
    """
    Extract 7 GLCM texture features from an MRI image.

    Parameters
    ----------
    source : str | bytes | Path
        File path or raw JPEG/PNG bytes.

    Returns
    -------
    dict with keys:
        entropy, correlation, energy, contrast, mean, std_dev, variance
    """
    # 1. Load + resize
    gray = _load_gray(source)
    gray = cv2.resize(gray, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LANCZOS4)

    # 2. Quantize: map [0,255] → [0, GRAY_LEVELS-1]
    quantized = (gray / 256.0 * GRAY_LEVELS).astype(np.uint8)
    quantized = np.clip(quantized, 0, GRAY_LEVELS - 1)

    # 3. Build GLCM (shape: levels × levels × len(distances) × len(angles))
    glcm = graycomatrix(
        quantized,
        distances=DISTANCES,
        angles=ANGLES,
        levels=GRAY_LEVELS,
        symmetric=True,
        normed=True,
    )
    # glcm shape: (8, 8, 1, 4)

    # 4. Extract scikit-image properties (averaged over angles)
    def prop(name: str) -> float:
        vals = graycoprops(glcm, name)   # (1, 4) — 1 distance × 4 angles
        return float(np.mean(vals))

    contrast    = prop("contrast")
    correlation = prop("correlation")
    energy      = prop("energy")
    # homogeneity = prop("homogeneity")  # extra, not in original 7

    # 5. Mean & Variance from marginal distribution
    #    p_i = marginal probability for gray level i (avg over angles)
    p_mat = glcm[:, :, 0, :]       # (8, 8, 4)
    p_mean = p_mat.mean(axis=2)    # (8, 8) — average over angles
    p_i = p_mean.sum(axis=1)       # (8,) — row marginal

    levels = np.arange(GRAY_LEVELS, dtype=np.float64)
    mean_val = float(np.sum(levels * p_i))
    variance = float(np.sum(((levels - mean_val) ** 2) * p_i))
    std_dev  = float(np.sqrt(max(variance, 0.0)))

    # 6. Entropy  (Eq. 8):  -Σ p * log2(p)
    p_nonzero = p_mean[p_mean > 0]
    entropy = float(-np.sum(p_nonzero * np.log2(p_nonzero)))

    return {
        "entropy":     round(entropy,     6),
        "correlation": round(correlation, 6),
        "energy":      round(energy,      6),
        "contrast":    round(contrast,    6),
        "mean":        round(mean_val,    6),
        "std_dev":     round(std_dev,     6),
        "variance":    round(variance,    6),
    }

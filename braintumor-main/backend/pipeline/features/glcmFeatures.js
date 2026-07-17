/**
 * glcmFeatures.js — GLCM Feature Extractor
 *
 * Extracts all 7 texture features from a normalized GLCM matrix.
 * Features are described in Section 3 (Feature Extraction) of the paper
 * and supply the input vector to the EDN-SVM classifier.
 *
 * ─── Features & Equations ────────────────────────────────────────────────────
 *
 * 1. Entropy (Eq. 8):
 *    Entropy = Σ_x Σ_y  T_xy * log(T_xy)
 *    → Measures uncertainty/randomness. Highest when all GLCM values are equal.
 *
 * 2. Correlation (Eq. 9):
 *    Correlation = Σ_x Σ_y  (x,y)*t(x,y) − μi*μj  /  σi*σj
 *    → Measures how closely related reference pixel is to its neighbour.
 *
 * 3. Energy (Eq. 10):
 *    Energy = Σ_x Σ_y  T²_xy
 *    → Sum of squared components. High when pixels are substantially similar.
 *
 * 4. Contrast (Eq. 11):
 *    Contrast = Σ_m m² * Σ_x Σ_y  T(x,y)²
 *    → Brightness difference between reference pixel and its neighbour.
 *
 * 5. Mean (Eq. 12):
 *    Mean (μ) = Σ_x  x * t(x)
 *    → Average brightness of the image or texture.
 *
 * 6. Standard Deviation (Eq. 13):
 *    σ = sqrt( Σ_x (x − μ)² * t(x) )
 *    → Spread of intensity values around the mean.
 *
 * 7. Variance (Eq. 14):
 *    Variance (σ²) = Σ_x (x − μ) * t(x)
 *    → Range of values in terms of relative intensity.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * Exported function:
 *  extractFeatures(glcmMatrix)
 *    @param {number[][]} glcmMatrix - Normalized GLCM from glcm.js
 *    @returns {{ entropy, correlation, energy, contrast, mean, stdDev, variance }}
 */

// TODO: Implement in backend implementation phase

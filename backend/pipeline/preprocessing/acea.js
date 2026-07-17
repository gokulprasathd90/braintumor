'use strict';

/**
 * acea.js — Adaptive Contrast Enhancement Algorithm (ACEA)
 *
 * Implements Section 3.2.1 of the paper, Equation 1.
 *
 * ─── Background ──────────────────────────────────────────────────────────────
 * MRI brain images contain three tissue classes whose mean intensities always
 * satisfy:  μT < μB < μV  (Tumor < Brain tissue < blood Vessels)
 *
 * The algorithm stretches the intensity range so that the diagnostically
 * important tumor region occupies the full [1, 255] output range, rather than
 * being compressed in a narrow band of the raw scanner output.
 *
 * ─── Equation 1 (Transform) ──────────────────────────────────────────────────
 *
 *   if Pmin ≤ Ix ≤ Pmax:
 *       I'x = ((Ix - Pmin) / (Pmax - Pmin)) * 254 + 1
 *   else:
 *       I'x = 0
 *
 *   where:
 *     Pmin = μT − k·σT      (lower bound — k = stdMultiplier = 3)
 *     Pmax = μV + k·σV      (upper bound)
 *     μT, μV  — adjusted class means derived from histogram peak N_V
 *     σT, σV  — standard deviations of the tumor / vessel class samples
 *
 * ─── Inference-time class estimation ─────────────────────────────────────────
 * At inference (no training labels), the three tissue classes are separated
 * by partitioning the grayscale histogram into three equal-thirds by intensity:
 *   T  [0  – 84]    darkest  → tumor / background
 *   B  [85 – 169]   mid      → healthy brain tissue
 *   V  [170 – 255]  brightest → blood vessels / bright structures
 *
 * Mean and σ are computed for each partition.  The histogram peak N_V is found
 * from the full image PDF, then used to shift the class means exactly as
 * described in the training-phase formula.
 *
 * ─── Exports ─────────────────────────────────────────────────────────────────
 *   enhanceImage(inputPath, outputPath)  → Promise<{ outputPath, stats }>
 *   enhanceById(imageId, inputPath)      → Promise<{ outputPath, stats }>
 */

const Jimp   = require('jimp');
const path   = require('path');
const config = require('../../config');
const { ensureDirectoryExists, generateOutputPath } = require('../../utils/imageUtils');
const logger = require('../../utils/logger');

const K             = config.acea.stdMultiplier;  // 3  (σ multiplier)
const INTENSITY_MIN = config.acea.intensityMin;   // 0
const INTENSITY_MAX = config.acea.intensityMax;   // 255

// ─── Histogram helpers ────────────────────────────────────────────────────────

/**
 * Build a 256-bin grayscale histogram from a Jimp image's bitmap.
 * Converts RGBA → grayscale using the standard luminance formula.
 *
 * @param   {Jimp}         img
 * @returns {Uint32Array}  hist[i] = number of pixels with intensity i
 */
function buildHistogram(img) {
  const hist = new Uint32Array(256);
  const { data, width, height } = img.bitmap;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;   // RGBA stride
      const r   = data[idx];
      const g   = data[idx + 1];
      const b   = data[idx + 2];
      // ITU-R BT.601 luminance — matches imageUtils.readPixelArray
      const gray = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
      hist[gray]++;
    }
  }
  return hist;
}

/**
 * Find the intensity level with the highest histogram count within [lo, hi].
 * Restricting the search range avoids the black-background peak (intensity 0)
 * dominating MRI images where the skull region is masked/black.
 *
 * @param   {Uint32Array} hist
 * @param   {number}      lo    lower bound (inclusive), default 1
 * @param   {number}      hi    upper bound (inclusive), default 255
 * @returns {number}  intensity in [lo, hi]
 */
function findPdfPeak(hist, lo = 1, hi = 255) {
  let peak    = lo;
  let peakVal = 0;
  for (let i = lo; i <= hi; i++) {
    if (hist[i] > peakVal) {
      peakVal = hist[i];
      peak    = i;
    }
  }
  return peak;
}

/**
 * Compute mean and standard deviation of pixels in a given intensity range
 * using the histogram (avoids re-scanning the bitmap).
 *
 * @param {Uint32Array} hist
 * @param {number}      lo   inclusive lower bound (0–255)
 * @param {number}      hi   inclusive upper bound (0–255)
 * @returns {{ mean: number, std: number, count: number }}
 */
function histStats(hist, lo, hi) {
  let count = 0;
  let sum   = 0;

  for (let i = lo; i <= hi; i++) {
    count += hist[i];
    sum   += hist[i] * i;
  }

  if (count === 0) {
    // Degenerate partition — fall back to midpoint
    const mid = (lo + hi) / 2;
    return { mean: mid, std: (hi - lo) / 6, count: 0 };
  }

  const mean = sum / count;

  let variance = 0;
  for (let i = lo; i <= hi; i++) {
    variance += hist[i] * (i - mean) * (i - mean);
  }
  const std = Math.sqrt(variance / count);

  return { mean, std, count };
}

// ─── Core ACEA transform ──────────────────────────────────────────────────────

/**
 * Estimate class statistics and derive Pmin / Pmax from the image histogram.
 *
 * Partition strategy (robust to large black MRI background):
 *   Background pixels (intensity 0) are excluded from all class statistics.
 *   The remaining pixels are divided into three equal-population thirds:
 *     T (darkest third)  → tumor / dark brain tissue
 *     B (middle third)   → healthy brain tissue
 *     V (brightest third) → blood vessels / bright structures
 *
 *   N_V = PDF peak within the B (brain) band [B_lo, B_hi], per paper Section 3.2.1.
 *
 * @param {Uint32Array} hist
 * @returns {{ Pmin: number, Pmax: number, muT: number, muV: number,
 *             nV: number, stdT: number, stdV: number }}
 */
function estimateThresholds(hist) {
  // Count total foreground pixels (exclude pure black background at 0)
  let totalFg = 0;
  for (let i = 1; i < 256; i++) totalFg += hist[i];

  // If image is nearly all black, fall back to safe defaults
  if (totalFg < 100) {
    return {
      Pmin: INTENSITY_MIN, Pmax: INTENSITY_MAX,
      muT: 0, muV: 255, nV: 128, stdT: 28, stdV: 28,
    };
  }

  // Find percentile-based partition boundaries on foreground pixels
  const third = totalFg / 3;
  let cumul = 0;
  let T_HI = 1, B_HI = 1;
  let foundT = false, foundB = false;

  for (let i = 1; i < 256; i++) {
    cumul += hist[i];
    if (!foundT && cumul >= third)      { T_HI = i; foundT = true; }
    if (!foundB && cumul >= 2 * third)  { B_HI = i; foundB = true; break; }
  }

  const T_LO = 1;
  const B_LO = T_HI + 1;
  const V_LO = B_HI + 1;
  const V_HI = 255;

  const statsT = histStats(hist, T_LO, T_HI);
  const statsV = histStats(hist, V_LO, V_HI);

  // N_V = PDF peak within the brain-tissue band [B_LO, B_HI]
  // This is the "highest PDF intensity for brain class" from the paper
  const nV = findPdfPeak(hist, B_LO, B_HI);

  // Curve-pattern Z offset: reference mean from tumor class
  const nZ  = statsT.mean;
  const muT = nV - nZ + statsT.mean;   // = nV
  const muV = nV - nZ + statsV.mean;   // shifts vessel mean by same offset

  // Equation 1: Pmin / Pmax with K·σ margins
  const Pmin = Math.max(INTENSITY_MIN, muT - K * statsT.std);
  const Pmax = Math.min(INTENSITY_MAX, muV + K * statsV.std);

  // Guard against degenerate case
  const safePmin = Pmin < Pmax ? Pmin : INTENSITY_MIN;
  const safePmax = Pmin < Pmax ? Pmax : INTENSITY_MAX;

  return {
    Pmin:  safePmin,
    Pmax:  safePmax,
    muT,
    muV,
    nV,
    stdT:  statsT.std,
    stdV:  statsV.std,
  };
}

/**
 * Apply the ACEA linear stretch transform (Equation 1) to every pixel.
 *
 * For Pmin ≤ Ix ≤ Pmax:   I'x = ((Ix - Pmin) / (Pmax - Pmin)) × 254 + 1
 * Otherwise:               I'x = 0
 *
 * Modifies img.bitmap.data in-place (RGBA channels: R=G=B=enhanced, A=255).
 *
 * @param {Jimp}   img
 * @param {number} Pmin
 * @param {number} Pmax
 * @returns {number} count of pixels mapped to 0 (out-of-range)
 */
function applyStretch(img, Pmin, Pmax) {
  const { data, width, height } = img.bitmap;
  const range = Pmax - Pmin;
  let clipped = 0;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;

      // Convert RGBA → grayscale
      const r    = data[idx];
      const g    = data[idx + 1];
      const b    = data[idx + 2];
      const gray = Math.round(0.299 * r + 0.587 * g + 0.114 * b);

      let enhanced;
      if (gray >= Pmin && gray <= Pmax) {
        // Equation 1: linear stretch into [1, 255]
        enhanced = Math.round(((gray - Pmin) / range) * 254 + 1);
      } else {
        enhanced = 0;
        clipped++;
      }

      // Write back as grayscale (R=G=B), preserve A=255
      data[idx]     = enhanced;
      data[idx + 1] = enhanced;
      data[idx + 2] = enhanced;
      data[idx + 3] = 255;
    }
  }

  return clipped;
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Enhance an MRI image using ACEA and save to outputPath.
 *
 * @param {string} inputPath   - Absolute path to the resized PNG
 * @param {string} outputPath  - Absolute path to save the enhanced PNG
 * @returns {Promise<{
 *   outputPath: string,
 *   stats: {
 *     Pmin: number, Pmax: number,
 *     muT: number,  muV: number,
 *     nV: number,
 *     stdT: number, stdV: number,
 *     clippedPixels: number,
 *     totalPixels: number
 *   }
 * }>}
 */
async function enhanceImage(inputPath, outputPath) {
  ensureDirectoryExists(path.dirname(outputPath));

  // 1. Load image
  const img = await Jimp.read(inputPath);

  // 2. Build grayscale histogram
  const hist = buildHistogram(img);

  // 3. Estimate Pmin / Pmax from histogram partitions
  const thresholds = estimateThresholds(hist);
  const { Pmin, Pmax } = thresholds;

  logger.info(
    `[ACEA] Pmin=${Pmin.toFixed(1)} Pmax=${Pmax.toFixed(1)} ` +
    `muT=${thresholds.muT.toFixed(1)} muV=${thresholds.muV.toFixed(1)} ` +
    `nV=${thresholds.nV} | ${path.basename(inputPath)}`
  );

  // 4. Apply Equation 1 in-place
  const clippedPixels = applyStretch(img, Pmin, Pmax);
  const totalPixels   = img.bitmap.width * img.bitmap.height;

  // 5. Save enhanced image as PNG
  await img.writeAsync(outputPath);

  logger.info(
    `[ACEA] Enhanced → ${path.basename(outputPath)} ` +
    `| clipped=${clippedPixels}/${totalPixels} ` +
    `(${((clippedPixels / totalPixels) * 100).toFixed(1)}%)`
  );

  return {
    outputPath,
    stats: {
      Pmin:          Math.round(Pmin),
      Pmax:          Math.round(Pmax),
      muT:           Math.round(thresholds.muT),
      muV:           Math.round(thresholds.muV),
      nV:            thresholds.nV,
      stdT:          parseFloat(thresholds.stdT.toFixed(2)),
      stdV:          parseFloat(thresholds.stdV.toFixed(2)),
      clippedPixels,
      totalPixels,
    },
  };
}

/**
 * Convenience wrapper: derives outputPath from imageId using
 * the standard pipeline naming convention.
 *
 * @param {string} imageId   - UUID from images table
 * @param {string} inputPath - Absolute path to the resized PNG
 * @returns {Promise<{ outputPath: string, stats: object }>}
 */
async function enhanceById(imageId, inputPath) {
  const outputPath = generateOutputPath(imageId, 'enhanced', 'png');
  return enhanceImage(inputPath, outputPath);
}

module.exports = { enhanceImage, enhanceById };

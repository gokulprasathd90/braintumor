'use strict';

/**
 * metrics.js — Evaluation Metric Computations
 *
 * Pure functions for all 7 evaluation metrics from the paper.
 * Each function is independently testable with no side effects.
 *
 * Confusion matrix terms (paper Section 4):
 *  tp — tumour correctly predicted as tumour   (true positive)
 *  tn — healthy correctly predicted as healthy (true negative)
 *  fp — healthy incorrectly predicted as tumour (false positive)
 *  fn — tumour incorrectly predicted as healthy (false negative)
 */

/**
 * Build confusion matrix from parallel prediction and label arrays.
 *
 * Label convention:
 *  1 = tumour (positive class)
 *  0 = healthy (negative class)
 *
 * @param {number[]} predictions  - array of 0/1 model outputs
 * @param {number[]} labels       - array of 0/1 ground truth labels
 * @returns {{ tp: number, tn: number, fp: number, fn: number }}
 */
function buildConfusionMatrix(predictions, labels) {
  if (predictions.length !== labels.length) {
    throw new Error('predictions and labels arrays must have the same length');
  }
  let tp = 0, tn = 0, fp = 0, fn = 0;
  for (let i = 0; i < predictions.length; i++) {
    const pred  = predictions[i];
    const truth = labels[i];
    if      (pred === 1 && truth === 1) tp++;
    else if (pred === 0 && truth === 0) tn++;
    else if (pred === 1 && truth === 0) fp++;
    else if (pred === 0 && truth === 1) fn++;
  }
  return { tp, tn, fp, fn };
}

/**
 * Accuracy — Equation 28
 * (tp + tn) / (tp + tn + fp + fn) * 100
 * Paper target: 97.93%
 *
 * @param {{ tp: number, tn: number, fp: number, fn: number }} cm
 * @returns {number} percentage 0–100
 */
function computeAccuracy({ tp, tn, fp, fn }) {
  const total = tp + tn + fp + fn;
  if (total === 0) return 0;
  return ((tp + tn) / total) * 100;
}

/**
 * Sensitivity (True Positive Rate) — Equation 31
 * TP / (TP + FN) * 100
 * Paper target: 92%
 *
 * @param {{ tp: number, fn: number }} cm
 * @returns {number} percentage 0–100
 */
function computeSensitivity({ tp, fn }) {
  const denom = tp + fn;
  if (denom === 0) return 0;
  return (tp / denom) * 100;
}

/**
 * Specificity (True Negative Rate) — Equation 32
 * TN / (TN + FP) * 100
 * Paper target: 98%
 *
 * @param {{ tn: number, fp: number }} cm
 * @returns {number} percentage 0–100
 */
function computeSpecificity({ tn, fp }) {
  const denom = tn + fp;
  if (denom === 0) return 0;
  return (tn / denom) * 100;
}

/**
 * PSNR — Peak Signal-to-Noise Ratio — Equation 30
 * 10 * log10(255² / MSE)
 * Paper target: 52.98
 * Higher values indicate better image quality preservation.
 *
 * @param {Uint8Array|number[]} originalPixels   - original pixel values
 * @param {Uint8Array|number[]} processedPixels  - processed pixel values
 * @returns {number} PSNR in dB
 */
function computePSNR(originalPixels, processedPixels) {
  if (originalPixels.length !== processedPixels.length) {
    throw new Error('Pixel arrays must have the same length for PSNR computation');
  }
  const n = originalPixels.length;
  if (n === 0) return 0;

  // Mean Squared Error
  let sumSqErr = 0;
  for (let i = 0; i < n; i++) {
    const diff = originalPixels[i] - processedPixels[i];
    sumSqErr += diff * diff;
  }
  const mse = sumSqErr / n;

  // Avoid log(0) — if MSE is 0 images are identical → infinite PSNR
  if (mse === 0) return Infinity;

  return 10 * Math.log10((255 * 255) / mse);
}

/**
 * Jaccard Coefficient (Intersection over Union) — Equation 29
 * |A ∩ B| / |A ∪ B|
 * A = segmented output binary mask (1 = tumor pixel)
 * B = ground truth binary mask     (1 = tumor pixel)
 * Higher values indicate better segmentation accuracy.
 *
 * @param {Uint8Array|number[]} segmentedMask   - binary mask from FCM
 * @param {Uint8Array|number[]} groundTruthMask - binary ground truth mask
 * @returns {number} Jaccard coefficient 0–1
 */
function computeJaccard(segmentedMask, groundTruthMask) {
  if (segmentedMask.length !== groundTruthMask.length) {
    throw new Error('Masks must have the same length for Jaccard computation');
  }
  let intersection = 0;
  let union = 0;
  for (let i = 0; i < segmentedMask.length; i++) {
    const a = segmentedMask[i] > 0 ? 1 : 0;
    const b = groundTruthMask[i] > 0 ? 1 : 0;
    if (a === 1 && b === 1) intersection++;
    if (a === 1 || b === 1) union++;
  }
  if (union === 0) return 0;
  return intersection / union;
}

/**
 * Bit Error Rate (BER)
 * fp / (fp + tn)
 * Lower values are better.
 *
 * @param {{ fp: number, tn: number }} cm
 * @returns {number} BER value 0–1
 */
function computeBER({ fp, tn }) {
  const denom = fp + tn;
  if (denom === 0) return 0;
  return fp / denom;
}

/**
 * Compute all metrics at once from predictions and labels arrays.
 * Convenience wrapper that builds the confusion matrix internally.
 *
 * @param {number[]} predictions
 * @param {number[]} labels
 * @returns {{
 *   accuracy: number,
 *   sensitivity: number,
 *   specificity: number,
 *   ber: number,
 *   tp: number, tn: number, fp: number, fn: number
 * }}
 */
function computeAllClassificationMetrics(predictions, labels) {
  const cm = buildConfusionMatrix(predictions, labels);
  return {
    accuracy:    parseFloat(computeAccuracy(cm).toFixed(4)),
    sensitivity: parseFloat(computeSensitivity(cm).toFixed(4)),
    specificity: parseFloat(computeSpecificity(cm).toFixed(4)),
    ber:         parseFloat(computeBER(cm).toFixed(6)),
    ...cm,
  };
}

module.exports = {
  buildConfusionMatrix,
  computeAccuracy,
  computeSensitivity,
  computeSpecificity,
  computePSNR,
  computeJaccard,
  computeBER,
  computeAllClassificationMetrics,
};

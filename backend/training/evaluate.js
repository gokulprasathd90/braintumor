/**
 * evaluate.js — Model Evaluation Script
 *
 * Computes all 7 evaluation metrics on the test set after training.
 * Can also be run standalone: node training/evaluate.js
 *
 * ─── Metrics Computed ────────────────────────────────────────────────────────
 *
 *  1. Accuracy (Equation 28):
 *     Accuracy = (tp + tn) / (tp + tn + fp + fn)
 *     Target: 97.93%
 *
 *  2. Sensitivity — True Positive Rate (Equation 31):
 *     Sensitivity = TP / (TP + FN) × 100
 *     Target: 92%
 *
 *  3. Specificity — True Negative Rate (Equation 32):
 *     Specificity = TN / (TN + FP) × 100
 *     Target: 98%
 *
 *  4. PSNR — Peak Signal-to-Noise Ratio (Equation 30):
 *     PSNR = 10 * log10(255² / MSE)
 *     Target: 52.98
 *
 *  5. Jaccard Coefficient (Equation 29):
 *     JC = A∩B / A∪B
 *     Compares segmented output to ground truth mask
 *
 *  6. Bit Error Rate (BER):
 *     BER = fp / (fp + tn)
 *     Lower is better
 *
 *  7. Computational Time:
 *     Wall-clock time in minutes for full pipeline per image
 *
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * Confusion matrix terms:
 *  tp = tumour correctly predicted as tumour
 *  tn = healthy correctly predicted as healthy
 *  fp = healthy incorrectly predicted as tumour
 *  fn = tumour incorrectly predicted as healthy
 *
 * Exported function:
 *  evaluateModel(model, testX, testY, segmentedPaths, groundTruthPaths)
 *    @returns {{ accuracy, sensitivity, specificity, psnr, jaccard, ber, computationalTime }}
 */

// TODO: Implement in backend implementation phase

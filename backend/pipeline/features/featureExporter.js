/**
 * featureExporter.js — GLCM Feature CSV Exporter
 *
 * Aggregates GLCM feature vectors for all training images and
 * exports them to dataset/features/glcm_features.csv.
 *
 * CSV columns:
 *  image_id, filename, label (0=healthy/1=tumor),
 *  entropy, correlation, energy, contrast, mean, std_dev, variance
 *
 * Used during training (training/train.js) to persist all extracted
 * features for analysis, reproducibility, and model input.
 *
 * Exported functions:
 *  appendFeatureRow(csvPath, featureRow)
 *    @param {string} csvPath     - Path to glcm_features.csv
 *    @param {object} featureRow  - { image_id, filename, label, ...features }
 *    @returns {Promise<void>}
 *
 *  exportAllFeatures(featuresArray, csvPath)
 *    @param {Array}  featuresArray - Array of feature row objects
 *    @param {string} csvPath       - Output CSV path
 *    @returns {Promise<void>}
 *
 * Dependencies:
 *  - csv-writer
 */

// TODO: Implement in backend implementation phase

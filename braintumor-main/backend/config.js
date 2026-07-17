'use strict';

require('dotenv').config();
const path = require('path');

const config = {
  // ─── Server ────────────────────────────────────────────────────────────────
  server: {
    port: parseInt(process.env.PORT, 10) || 5000,
    host: process.env.HOST || 'localhost',
    env: process.env.NODE_ENV || 'development',
  },

  // ─── CORS ──────────────────────────────────────────────────────────────────
  cors: {
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true,
  },

  // ─── Paths ─────────────────────────────────────────────────────────────────
  paths: {
    // Runtime upload directory (Multer saves here)
    uploadDir: path.resolve(
      __dirname,
      process.env.UPLOAD_DIR || '../uploads'
    ),
    // Dataset directories
    datasetDir: path.resolve(
      __dirname,
      process.env.DATASET_DIR || '../dataset'
    ),
    processedDir: path.resolve(__dirname, '../dataset/processed'),
    resizedDir: path.resolve(__dirname, '../dataset/processed/resized'),
    enhancedDir: path.resolve(__dirname, '../dataset/processed/enhanced'),
    denoisedDir: path.resolve(__dirname, '../dataset/processed/noise_removed'),
    segmentedDir: path.resolve(__dirname, '../dataset/processed/segmented'),
    featuresDir: path.resolve(__dirname, '../dataset/features'),
    // Model artifact
    modelPath: path.resolve(
      __dirname,
      process.env.MODEL_PATH || './models/edn_svm.json'
    ),
    // Logs
    logsDir: path.resolve(__dirname, '../logs'),
  },

  // ─── Database ──────────────────────────────────────────────────────────────
  database: {
    path: path.resolve(
      __dirname,
      process.env.DB_PATH || './database/brain_tumor.db'
    ),
  },

  // ─── Multer Upload ─────────────────────────────────────────────────────────
  upload: {
    maxFileSizeBytes: 10 * 1024 * 1024, // 10 MB
    allowedMimeTypes: ['image/jpeg', 'image/png'],
    allowedExtensions: ['.jpg', '.jpeg', '.png'],
    fieldName: 'image', // multipart field name expected from client
  },

  // ─── Image Processing ──────────────────────────────────────────────────────
  image: {
    targetWidth: 256,
    targetHeight: 256,
  },

  // ─── ACEA Parameters ───────────────────────────────────────────────────────
  // Adaptive Contrast Enhancement Algorithm — Section 3.2.1
  acea: {
    sampleSize: 100,           // number of random voxels to sample per class
    stdMultiplier: 3,          // σ multiplier for Pmin / Pmax (Equation 1)
    intensityMin: 0,
    intensityMax: 255,
  },

  // ─── Median Filter Parameters ──────────────────────────────────────────────
  // Section 3.2.2, Equation 2
  medianFilter: {
    windowSize: 3,             // 3×3 neighbourhood window
  },

  // ─── FCM Parameters ────────────────────────────────────────────────────────
  // Fuzzy C-Means — Section 3.3, Equations 3–7
  fcm: {
    clusters: 3,               // C = 3: tumor, brain tissue, vessels
    fuzziness: 2,              // n — fuzziness weighting exponent ∈ [1, ∞]
    epsilon: 0.01,             // ε — convergence termination threshold
    maxIterations: 100,        // maximum number of iterations
  },

  // ─── GLCM Parameters ───────────────────────────────────────────────────────
  // Gray-Level Co-occurrence Matrix — Section 3, Equations 8–14
  glcm: {
    grayLevels: 16,            // quantization levels (rows = columns per paper)
    distance: 1,               // pixel pair distance offset
    angles: [0, 45, 90, 135], // co-occurrence directions in degrees
  },

  // ─── EDN-SVM Hyperparameters ───────────────────────────────────────────────
  // Ensemble Deep Neural SVM — Section 3.4, Algorithm 1
  ednSvm: {
    inputSize: 7,              // GLCM feature vector length
    featureSize: 7,            // number of nodes in central feature layer
    hiddenUnits: 32,           // hidden units per MLP
    kernel: 'rbf',             // kernel type: 'rbf' | 'polynomial' | 'sigmoid'
    epochs: 100,               // training epochs
    lambda: 0.001,             // λ — gradient ascent learning rate (Eq. 24)
    T1: 0.01,                  // T1 — bias constraint penalty (Eq. 24)
    T2: 0.01,                  // T2 — sparsity penalty (Eq. 24)
    C: 1.0,                    // F — regularization parameter (Eq. 15)
    epsilon: 0.1,              // ξ-insensitive tube width (Eq. 15)
    gamma: 0.5,                // γ — RBF kernel width
  },

  // ─── SVR Parameters ────────────────────────────────────────────────────────
  // Support Vector Regression — Section 3.4.1, Equations 15–19
  svr: {
    kernel: 'rbf',
    C: 1.0,                    // regularization parameter F
    epsilon: 0.1,              // ξ-insensitive tube
    gamma: 0.5,                // kernel coefficient
    degree: 3,                 // polynomial kernel degree
    coef0: 0.0,                // polynomial/sigmoid kernel coefficient r
  },
};

module.exports = config;

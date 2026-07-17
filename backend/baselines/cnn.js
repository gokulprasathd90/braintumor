/**
 * cnn.js — CNN Baseline Model
 *
 * Convolutional Neural Network baseline for comparison with EDN-SVM.
 * Reference: [22] Martini & Oermann, "Intraoperative brain tumour
 * identification with deep learning", Nat. Rev. Clin. Oncol. 17(4) 2020.
 *
 * Architecture (TensorFlow.js):
 *  - Conv2D layers with ReLU activation
 *  - MaxPooling2D layers
 *  - Flatten
 *  - Dense layers
 *  - Output: sigmoid (binary classification)
 *
 * Input: Raw MRI images (256×256×1 grayscale)
 * Output: 0 (healthy) | 1 (tumor)
 *
 * Note (from paper):
 *  "CNN requires a vast amount of training data to categorise tumour images."
 *  This is a key disadvantage compared to the proposed EDN-SVM.
 *
 * Exported class: CNNBaseline
 *  build()          — Creates TF.js Sequential model
 *  train(X, y)      — Trains on image pixel arrays
 *  predict(x)       — Returns binary prediction
 *  evaluate(X, y)   — Returns all 7 metrics
 */

// TODO: Implement in backend implementation phase

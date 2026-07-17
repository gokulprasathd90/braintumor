/**
 * ann.js — Artificial Neural Network Baseline
 *
 * ANN baseline for comparison with EDN-SVM.
 * Reference: [24] Arunkumar et al., "Fully automatic model-based
 * segmentation and classification approach for MRI brain tumor using
 * artificial neural networks", Concurrency Comput. Pract. Ex. 32(1) 2020.
 *
 * Architecture (TensorFlow.js):
 *  - Fully connected (Dense) layers only — no convolutional layers
 *  - Input: GLCM feature vector (7 features)
 *  - Hidden layers with ReLU activation
 *  - Output: sigmoid (binary classification)
 *
 * Note (from paper):
 *  "The ANN is a model of hardware dependency, and it exhibits
 *   behaviour that cannot be described."
 *  This is a key disadvantage compared to the proposed EDN-SVM.
 *
 * Exported class: ANNBaseline
 *  build()        — Creates TF.js Sequential dense model
 *  train(X, y)    — Trains on GLCM feature vectors
 *  predict(x)     — Returns binary prediction
 *  evaluate(X, y) — Returns all 7 metrics
 */

// TODO: Implement in backend implementation phase

/**
 * rfc.js — Random Forest Classifier Baseline
 *
 * Random Forest Classifier baseline for comparison with EDN-SVM.
 * Reference: [23] Soltaninejad et al., "Supervised learning based multimodal
 * MRI brain tumour segmentation using texture features from supervoxels",
 * Comput. Methods Progr. Biomed. 157 (2018) 69–84.
 *
 * Input: GLCM feature vectors (same 7 features used by EDN-SVM)
 * Output: 0 (healthy) | 1 (tumor)
 *
 * Note (from paper):
 *  "The fundamental drawback of RFC is that it may be rendered useless
 *   and unreasonably sluggish for use in real-time prediction when used
 *   with an excessively large number of trees."
 *
 * Implementation:
 *  - Uses JavaScript random forest library (ml-random-forest or custom)
 *  - Takes same GLCM feature vectors as EDN-SVM for fair comparison
 *  - Number of trees configurable via config.js
 *
 * Exported class: RFCBaseline
 *  train(X, y)    — Trains random forest on GLCM features
 *  predict(x)     — Returns binary prediction
 *  evaluate(X, y) — Returns all 7 metrics
 */

// TODO: Implement in backend implementation phase

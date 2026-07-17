# 03 — FCM Segmentation Notes

## Fuzzy C-Means Algorithm
- Reference: Section 3.3, Equations 3–7
- Clusters C = 3: Tumor, Brain tissue, Vessels
- Fuzziness parameter n ∈ [1, ∞]
- Convergence threshold ε
- Max iterations: configurable

## Cluster Interpretation
- Cluster 1 (lowest mean): Brain tumor region
- Cluster 2 (middle mean): Healthy brain tissue
- Cluster 3 (highest mean): Blood vessels

## Notes
<!-- To be populated during implementation -->
- [ ] Plot segmented images (Fig. 6 equivalent)
- [ ] Record number of iterations until convergence per image
- [ ] Plot objective function Y vs iteration for sample images
- [ ] Compare cluster centers between healthy and tumor images
- [ ] Visualize membership matrix as heatmap

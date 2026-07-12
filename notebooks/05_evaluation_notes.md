# 05 — Evaluation Notes

## Target Metrics (from paper — Anantharajan et al. 2024)
| Metric             | Target     | Equation |
|--------------------|------------|----------|
| Accuracy           | 97.93%     | Eq. 28   |
| Sensitivity        | 92%        | Eq. 31   |
| Specificity        | 98%        | Eq. 32   |
| PSNR               | 52.98      | Eq. 30   |
| Computational Time | Lowest     | —        |
| Jaccard Coeff.     | Highest    | Eq. 29   |
| BER                | Lowest     | —        |

## Baseline Models Compared
| Model   | Reference | Key Disadvantage (from paper)                         |
|---------|-----------|-------------------------------------------------------|
| CNN     | [22]      | Requires vast training data                           |
| RFC     | [23]      | Slow for real-time with many trees                    |
| ANN     | [24]      | Hardware-dependent, unexplainable behaviour           |
| R-CNN   | [25]      | ~47 seconds per test image, not real-time             |
| EDN-SVM | Proposed  | Best across all metrics                               |

## Notes
<!-- To be populated during implementation -->
- [ ] Generate confusion matrix for each model
- [ ] Plot ROC curves for each model
- [ ] Reproduce Figures 9–14 (comparison bar charts)
- [ ] Document final achieved metrics vs paper targets

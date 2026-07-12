# 04 — GLCM Feature Analysis

## Feature Extraction
- Reference: Section 3 (Feature Extraction), Equations 8–14
- Input: FCM-segmented image
- Output: 7-element feature vector per image

## Features
| Feature    | Equation | Description                               |
|------------|----------|-------------------------------------------|
| Entropy    | Eq. 8    | Measures uncertainty/randomness           |
| Correlation| Eq. 9    | Reference vs neighbour pixel relationship |
| Energy     | Eq. 10   | Homogeneity measure                       |
| Contrast   | Eq. 11   | Brightness difference                     |
| Mean       | Eq. 12   | Average brightness                        |
| Std Dev    | Eq. 13   | Spread around mean                        |
| Variance   | Eq. 14   | Range of intensity values                 |

## Notes
<!-- To be populated during implementation -->
- [ ] Plot feature distributions: healthy vs tumor for each feature
- [ ] Compute feature correlation matrix
- [ ] Box plots per feature per class
- [ ] Identify most discriminative features (highest separation between classes)
- [ ] Verify glcm_features.csv values match manual calculations

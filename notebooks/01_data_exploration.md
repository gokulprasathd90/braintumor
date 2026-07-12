# 01 — Data Exploration

## Dataset Overview
- Source: Kaggle — Brain MRI Images for Brain Tumor Detection
- Total images: 255 T1-mode MRI scans
- Healthy class: 98 images
- Tumor class:  155 images
- Class imbalance ratio: ~1.58:1 (tumor:healthy)

## Image Characteristics
- Format: JPEG / PNG
- Mode: T1-weighted MRI (grayscale)
- Dimensions: Varying (requires resize to 256×256)
- Refer to Fig. 3(A) of paper — images have unique widths and heights

## Notes
- Images are resized to uniform 256×256 before preprocessing (Fig. 3B)
- Dataset split: 80% train (204 images) / 20% test (51 images), stratified
- Random seed fixed for reproducibility

## Analysis Tasks
<!-- To be populated during implementation -->
- [ ] Plot class distribution bar chart
- [ ] Plot sample images grid (healthy vs tumor)
- [ ] Compute pixel intensity histograms per class
- [ ] Document min/max/mean dimensions before resize

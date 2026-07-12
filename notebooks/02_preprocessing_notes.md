# 02 — Preprocessing Notes

## ACEA (Adaptive Contrast Enhancement Algorithm)
- Reference: Section 3.2.1, Equation 1
- Three tissue classes: Tumor (T), Brain (B), Vessel (V)
- Key relationship: μT < μB < μV (always holds)
- Pmin = μT − 3σT  |  Pmax = μV + 3σV
- Transform maps intensities to [0, 255]

## Median Filter
- Reference: Section 3.2.2, Equation 2
- Window size: 3×3 (default)
- Removes salt-and-pepper noise
- Preserves edge information

## Notes
<!-- To be populated during implementation -->
- [ ] Compare histograms before/after ACEA per class
- [ ] Plot Curve Pattern Z vs new image PDF
- [ ] Visualize Pmin/Pmax on histogram (Fig. 4 equivalent)
- [ ] Measure PSNR improvement after median filter
- [ ] Compare filtered vs unfiltered images side by side (Fig. 5 equivalent)

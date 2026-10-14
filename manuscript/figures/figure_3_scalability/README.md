# Figure 3: scalability and resource use

These plots are newly generated representations of the **archived v0.1.0** Experiment 2 results. They do not constitute new benchmark measurements, and are **not** valid as v1.0.0 performance results.

`verify_figure3.py` performs independent standard-library checks of all 105 execution records, 21 configuration summaries, fixed source SHA-256 digests, median/interquartile ranges, and the key scaling/contrast statistics. `render_figure3.py` verifies evidence before rendering. Requires matplotlib and NumPy. The source analysis remains `experiments/experiment_2_scalability/analysis/analyse_formal_results.py`.

```
python3 manuscript/figures/figure_3_scalability/verify_figure3.py
python3 manuscript/figures/figure_3_scalability/render_figure3.py
```

Outputs: `Figure3_A`–`Figure3_D` (editable-text SVG and 300 dpi PNG), plus `Figure3_NEXCISION_scalability` (assembled 2 × 2). The renderer reads **both** the immutable measured- and summary-level TSV records. Each panel shows five individual measurements per configuration with deterministic display-only jitter and explicit medians; panels A and B share the same five runs per input-size configuration. The publication palette is navy `#1F3B5C`, teal `#1B9E77`, amber `#D89C1D`, and charcoal `#333333`. Marker shape, luminance and line type provide redundant encodings in grayscale.

## Interpretation decisions

- **Panel A:** original linear-model fit to six medians has intercept −0.1811 s and predicts negative time at ~10 MB. It cannot be fully displayed on logarithmic axes. The dashed line in the revised visualization is instead the independently verified log–log fit restricted to inputs ≥~100 MB (exponent 0.9781), clearly described in the legend. The original-scale linear fit R² of 0.998637 remains a separate manuscript statistic. The smallest case had high between-repetition variability (CV ~33.6%), hence its exclusion from the log–log exponent is prespecified in the original analysis. All five raw elapsed times, including an unusually slow run, are now visible.
- **Panel B:** dashed line is the original-scale linear model for peak RSS; its intercept is positive. Both axes remain logarithmic.
- **Panel C:** the former bars/IQR display is replaced with five individual points per category (circle/square/triangle) and a black median stroke. The design changes taxa/row count jointly and input bytes vary from 0.4581 to 0.4887 GiB, hence the figure demonstrates an association with matrix shape, not a controlled causal estimate for site-row count alone.
- **Panel D:** y-axis begins at zero rather than cropping to 4.35 s, making the 13.53% change visibly proportional. The line joins medians and each group shows five individual measured runs; actual medians are unchanged.

All source performance records refer to five randomized measured repetitions after one unreported warm-up on one pinned logical CPU of an exclusively allocated AMD EPYC 9374F system with node-local XFS storage and warm page cache. The benchmark runner's `correct` flag covers row count, dimensions, exit status and output presence, not a full per-base oracle comparison (see separate correctness Experiment 1).

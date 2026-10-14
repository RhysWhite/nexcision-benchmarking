# Figure 3 assembly and historical plots

**Publication assets** are now in `manuscript/figures/figure_3_scalability/` (four separate panels plus a 2 × 2 composite, editable SVG and 300-dpi PNG, with verification and generation scripts). The legend is `manuscript/figure_legends/FIGURE3_LEGEND.md`.

The earlier `figure_2A_runtime_scaling.*` ... `figure_2D_interval_count.*` files in this directory remain unchanged **archival source plots** from the original Experiment 2 analysis. Those historical file names are not the manuscript figure numbering. Panel A of the updated Figure 3 shows the predeclared >=~100 MB log–log fit, rather than the original six-point linear fit whose negative intercept cannot be displayed over the whole data range on logarithmic axes. Panel C uses deliberately noncausal wording for its shape comparison. Do not replace the archived originals.

Regenerate the publication artwork via `python3 manuscript/figures/figure_3_scalability/render_figure3.py` from the benchmarking-repository root.

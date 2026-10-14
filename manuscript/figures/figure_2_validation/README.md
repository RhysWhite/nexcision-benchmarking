# Figure 2 — historical v0.1.0 validation evidence

This folder preserves editable vector artwork, a raster export, a deterministic
renderer, and an independent records-verification script for the seven-layer
validation diagram. The source numbers are from **Experiment 1**, not the
scalability benchmark in Experiment 2.

From the root of `nexcision-benchmarking`:

```bash
python3 manuscript/figures/figure_2_validation/verify_figure2.py
python3 manuscript/figures/figure_2_validation/render_figure2.py
```

`verify_figure2.py` requires only the Python standard library. Rendering uses
Matplotlib. The verification script checks the archived summary, underlying
TSV rows and recorded SHA-256 hashes. It does **not** rerun the historical
property tests or reconstruct genuine SPANDx matrix inputs, which were not
released in this repository.

Before publication with **NEXCISION v1.0.0**, rerun the complete validation
suite against its frozen wheel, archive the new results and update this figure,
its rendering script and the manuscript together. Do not label archived
v0.1.0 counts as independently verified v1.0.0 results.

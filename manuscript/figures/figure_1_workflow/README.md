# Figure 1 — NEXCISION coordinate-row excision

Publication-oriented correction of `Figure1_Workflow.png`.

## Design corrections

- Replaced the former A/C/G/T/A/G **column headers** with five actual taxon labels: `Iso1`–`Iso5`.
- Each row now displays exactly five states, matching five taxa.
- The example contains five distinct genomic-site coordinates; selected interval `18000–19000` matches exactly the three inclusive positions `18000`, `18500`, and `19000`.
- Output displays exactly the original `16000` and `20000` rows with identical five-character state strings.
- Added explicit `NTAX=5`, `NCHAR=5` (input), `NTAX=5`, `NCHAR=2` (output).
- No ellipses or implied additional rows: the example shows the entire example matrix.
- Made all graphics and text editable through SVG; high-resolution PNG is a derivative.

## Files

- `Figure1_NEXCISION_corrected.svg` — primary publication source (1900 × 870 viewBox).
- `Figure1_NEXCISION_corrected.png` — 3800 × 1740 raster export.
- `render_figure1.py` — deterministic figure-generation source, requiring CairoSVG for PNG.
- `example_input.nex`, `example_regions.tsv`, `example_expected_filtered.nex` — exact runnable test case.
- `verify_figure1.py` — validates the example against your current locally importable NEXCISION code.
- `Figure1_legend.txt` — recommended manuscript figure legend.

## Reproduce

From the directory containing this figure package:

```bash
python3 render_figure1.py
PYTHONPATH="$HOME/github/nexcision/src" python3 verify_figure1.py
```

To reproduce via CLI (optional, with package installed):

```bash
nexcise example_input.nex example_regions.tsv --output actual_filtered.nex --counts actual_counts.tsv
cmp actual_filtered.nex example_expected_filtered.nex
```

Source and graphics represent an **illustrative synthetic example**, not a SPANDx-derived biological observation. No release/version upgrade is implied.

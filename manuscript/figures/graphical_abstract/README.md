# NEXCISION graphical abstract

A deterministic, fully code-rendered SVG and 4800 × 2700 PNG graphical abstract.
All visual elements (including matrices, intervals, arrows and typography) are SVG
shapes or live SVG text, rather than images pasted into a drawing.

## Rebuild

Requires Python 3.10+ and `svgwrite`, `cairosvg` and `Pillow` for verification.

```bash
python -m pip install svgwrite cairosvg pillow
python render_graphical_abstract.py
python verify_graphical_abstract.py
```

The script produces `GraphicalAbstract_NEXCISION.svg` and
`GraphicalAbstract_NEXCISION.png` in this directory. For a different PNG
resolution use `--png-width`, but the default verification expects 4800 px.

## Scientific contract

- The example is an illustrative **single-reference** transposed matrix.
- All row states are declared once in `ROWS`. Filtered rows are generated with
  a **1-based inclusive** interval `[18000,19000]`. Six input site rows yield
  three removed and three retained site rows; `NCHAR` changes 6 → 3 and
  `NTAX` remains 5.
- The 4.83 GiB / 24.24 s / ~23.4 GiB peak RSS performance data describe the
  **frozen NEXCISION v0.1.0 benchmark** on a single pinned logical CPU, not an
  independently benchmarked current software version.
- Independent-validation claims are the archived original v0.1.0 findings:
  oracle comparison, 1,000 synthetic matrices, and detection of 12/12
  deliberate software mutations.
- Intended scope is narrower than the general NEXUS format. Input matrices
  require one reference-coordinate axis; unsupported character-indexed
  metadata is rejected rather than silently rewritten.
- Outputs are `filtered.nex`, optional counts (when `--counts` is supplied),
  and optional JSON report/checksums (when `--report` is supplied).
- Repository integration examples exist for shell and Snakemake workflows.

## Verification

`verify_graphical_abstract.py` checks the example's exact row arithmetic,
expected live-text claims, SVG geometry, PNG dimensions, and the exact SHA-256
bytes from repeating a build **in the same rendering environment**. Fonts and
rendering libraries are environment-sensitive, so binary identity across
uncontrolled different computers is not claimed.

## Asset structure

Place these files at:

`manuscript/figures/graphical_abstract/`

The final journal canvas/size should be checked against the journal's latest
specific graphical-abstract requirements before submission.

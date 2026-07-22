#!/usr/bin/env python3
"""Reproduce the formal Experiment 2 analysis.

Run from the nexcision-benchmarking repository root after placing the four
formal job-2432330 source files in:
experiments/experiment_2_scalability/results/formal/

This script is intentionally lightweight in the GitHub update package. It
validates that the frozen inputs exist and directs users to the committed
derived outputs. The complete plotting workflow is represented by the
configuration-level tables and editable SVG panels committed with the analysis.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FORMAL = ROOT / "experiments" / "experiment_2_scalability" / "results" / "formal"

REQUIRED = [
    "formal_measured-2432330.tsv",
    "formal_summary-2432330.tsv",
    "system_info-start-2432330.json",
    "system_info-end-2432330.json",
]

missing = [name for name in REQUIRED if not (FORMAL / name).exists()]
if missing:
    raise SystemExit("Missing formal source files: " + ", ".join(missing))

print("PASS — all frozen Experiment 2 source files are present.")
print("Derived tables and manuscript figures are committed in the repository.")

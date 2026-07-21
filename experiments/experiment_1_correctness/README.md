# Experiment 1 — formal correctness validation

## Question

Does NEXCISION remove exactly the intended coordinate-labelled rows, preserve every retained row and state, update NEXUS dimensions correctly, report interval-specific counts accurately, and fail safely on malformed inputs?

## Status

**Complete: all predefined acceptance criteria passed.**

| Component | Result |
|---|---:|
| Genuine SPANDx matrices | 3 files; 6/6 checks passed |
| Software unit tests | 26/26 passed |
| Fixed correctness and preservation cases | 17/17 passed |
| All-sites safety case | 1/1 passed |
| Malformed-input and output-safety cases | 26/26 passed |
| Deterministic synthetic matrices | 1,000/1,000 passed |
| Property-based invariants | 9/9 passed across 1,800 examples |
| Deliberate source mutants detected | 12/12 |

The full interpretation is in [`validation/EXPERIMENT1_REPORT.md`](validation/EXPERIMENT1_REPORT.md). Machine-readable headline results are in [`validation/experiment1_summary.json`](validation/experiment1_summary.json).

## Directory contents

```text
experiment_1_correctness/
├── NEXCISION_SPECIFICATION.md   # behaviour evaluated
├── software_tests/              # snapshot of the software unit tests
└── validation/
    ├── oracle/                  # independent naïve truth checker
    ├── fixed_cases/             # small human-readable regression cases
    ├── safety_cases/            # empty-matrix safety case
    ├── synthetic/               # generators, manifests and results
    ├── property/                # property-based invariants
    ├── mutation/                # deliberate source mutants
    └── *.tsv / *.json / *.md    # results and reports
```

The full generated 1,000-case matrix corpus is not committed. It is reconstructed from the tracked generator and manifest.

## Reproduce the lightweight suite

From the repository root, after installing the environment and wheel:

```bash
python scripts/run_experiment1_light.py
```

This runs:

- 26 unit tests;
- 17 fixed correctness/preservation cases;
- the all-sites safety case;
- 26 malformed-input/output-safety cases;
- the ten-case synthetic pilot;
- property-based validation;
- mutation testing.

## Reproduce the full 1,000-case corpus

```bash
python scripts/run_experiment1_full.py
```

The command regenerates the corpus locally, validates all 1,000 matrices against the independent oracle, and writes fresh results under `validation/synthetic/`.

## Interpretation boundary

Experiment 1 validates the explicitly documented SPANDx-style transposed NEXUS use case. It does not establish runtime or memory scalability, biological validity of supplied intervals, compatibility with every legal NEXUS representation, or support for repeated coordinates across multiple contigs.

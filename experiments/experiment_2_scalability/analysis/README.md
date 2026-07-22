# Experiment 2 analysis

This directory contains the reproducible analysis entry point for the frozen
formal Experiment 2 run.

## Install analysis dependencies

```bash
python -m pip install -r environments/experiment2-analysis-requirements.txt
```

## Reproduce and validate

From the repository root:

```bash
python experiments/experiment_2_scalability/analysis/analyse_formal_results.py \
  --job-id 2432330
```

Before producing outputs, the script verifies:

- 105 measured runs across 21 configurations;
- five repetitions per configuration;
- zero non-zero return codes or correctness failures;
- deterministic filtered-output checksums;
- retained-row, `ntax` and `nchar` agreement;
- byte-for-byte consistency of the stored configuration summary with the
  measured table's medians and type-7 quartiles;
- matching Slurm job, host, repository commit, software version and wheel
  checksum across the start and end system snapshots.

It then regenerates:

```text
experiments/experiment_2_scalability/results/formal/derived/
manuscript/figures/experiment_2/
manuscript/tables/experiment2_key_results.tsv
```

The compact measured and summary TSV files are the source of truth. Do not
manually edit derived tables or plotted values.

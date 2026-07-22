# Experiment 2 analysis

This directory contains the reproducible analysis entry point for the frozen
formal Experiment 2 run.

## Install analysis dependencies

```bash
python -m pip install -r environments/experiment2-analysis-requirements.txt
```

## Reproduce derived tables and figures

From the repository root:

```bash
python experiments/experiment_2_scalability/analysis/analyse_formal_results.py \
  --job-id 2432330
```

The script validates the expected 105 measured executions and 21
configurations, then regenerates:

```text
experiments/experiment_2_scalability/results/formal/derived/
manuscript/figures/experiment_2/
```

The compact measured and summary TSV files are the source of truth. Do not
manually edit derived tables or plotted values.

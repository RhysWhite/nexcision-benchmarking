# Formal Experiment 2 results

This directory separates compact source measurements from derived analyses.

## Source measurements committed to Git

```text
formal_measured-2432330.tsv
formal_summary-2432330.tsv
system_info-start-2432330.json
system_info-end-2432330.json
```

These files are small, auditable and sufficient to reproduce the reported
configuration summaries and figures.

## Derived outputs

```text
derived/experiment2_key_results.tsv
derived/experiment2_qc_by_configuration.tsv
```

Derived files must be regenerated with:

```bash
python experiments/experiment_2_scalability/analysis/analyse_formal_results.py \
  --job-id 2432330
```

Generated NEXUS matrices, filtered outputs, virtual environments and repeated
Slurm logs are not committed. Additional formal artefacts such as the case
inventory, warm-up table and full Slurm logs may be archived with a tagged
release or research-data deposit.

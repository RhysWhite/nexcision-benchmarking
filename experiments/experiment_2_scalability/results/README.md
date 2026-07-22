# Experiment 2 results

This directory separates the instrumentation pilot from the frozen formal
benchmark.

## Pilot

`pilot/` contains the compact record from Slurm job `2432141`. All nine pilot
executions were correct and deterministic within configuration. These runs
validated the instrumentation only and are not used as manuscript performance
measurements.

## Formal benchmark

`formal/` contains the compact source measurements from Slurm job `2432330`
and the derived analysis tables.

The committed source files are:

```text
formal/formal_measured-2432330.tsv
formal/formal_summary-2432330.tsv
formal/system_info-start-2432330.json
formal/system_info-end-2432330.json
```

Derived outputs are stored under:

```text
formal/derived/
```

Regenerate them with:

```bash
python experiments/experiment_2_scalability/analysis/analyse_formal_results.py \
  --job-id 2432330
```

Generated NEXUS matrices, filtered outputs, virtual environments and repeated
Slurm logs are not committed. Additional formal artefacts such as the case
inventory, warm-up table, benchmark context and full Slurm logs may be archived
with a tagged release or research-data deposit.

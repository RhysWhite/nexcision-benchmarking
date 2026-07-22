# Frozen formal benchmark: Slurm job 2432330

This directory contains the compact source record and derived tables used for
the Experiment 2 manuscript claims.

## Source of truth

```text
formal_measured-2432330.tsv
formal_summary-2432330.tsv
system_info-start-2432330.json
system_info-end-2432330.json
SOURCE_SHA256SUMS.txt
```

`formal_summary-2432330.tsv` was independently regenerated from the measured
run table during repository audit and matched byte-for-byte.

## Derived outputs

```text
derived/experiment2_key_results.tsv
derived/experiment2_qc_by_configuration.tsv
```

Regenerate the derived outputs and manuscript figures from the repository root:

```bash
python -m pip install -r environments/experiment2-analysis-requirements.txt
python experiments/experiment_2_scalability/analysis/analyse_formal_results.py \
  --job-id 2432330
```

The multi-gigabyte generated matrices and filtered outputs are intentionally
not committed.

## Provenance boundary

The committed compact record does not currently include the original
`formal_inventory`, warm-up table, `benchmark_context`, job-level checksum file
or generated-input hashes. These omissions do not alter the reported medians or
correctness results, which are fully supported by the measured table, summary
and system snapshots. However, adding the original small job artefacts as a
tagged-release asset would strengthen archival provenance and document the
historical CPU-affinity and warm-up record directly.

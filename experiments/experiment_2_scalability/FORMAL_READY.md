# Formal benchmark readiness

The instrumentation pilot completed successfully on `kscprod-bio1` with 9/9
correct executions. Exclusive allocation on the same node was also confirmed.

The new formal runner was independently smoke-tested before packaging:

- 2/2 generated configurations passed warm-up checks;
- 4/4 measured executions passed;
- filtered outputs were deterministic within each configuration;
- report-enabled output was created and validated;
- summary TSV and JSON files were generated successfully.

This smoke test used tiny local matrices and is not a manuscript performance
result. The HPC smoke job must still be run after the updated repository is
pulled onto the cluster.

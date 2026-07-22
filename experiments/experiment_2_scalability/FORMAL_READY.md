# Formal benchmark completion record

The instrumentation pilot completed successfully on `kscprod-bio1`, followed
by a successful exclusive-node smoke test.

The frozen formal benchmark was then completed as Slurm job `2432330`:

- 21/21 configurations generated successfully;
- 21/21 unreported warm-up executions passed;
- 105/105 measured executions passed correctness checks;
- all repeated filtered outputs were deterministic within configuration;
- summary TSV and JSON outputs were generated;
- start and end system snapshots documented the benchmark environment.

The formal run used NEXCISION v0.1.0, one pinned CPU, an exclusive allocation
of `kscprod-bio1`, and node-local XFS storage. The measured and summary TSV
files are the source of truth for the Experiment 2 manuscript results.

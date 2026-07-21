# Formal Experiment 2 benchmark protocol

## Objective

Measure how NEXCISION v0.1.0 wall time, CPU time, peak resident memory and
application throughput change with input size, matrix shape, interval count,
interval geometry and provenance reporting.

Experiment 1 already established filtering correctness. Every Experiment 2 run
still checks retained-row count, `ntax`, `nchar`, required outputs and output
checksum before it is accepted.

## Frozen platform

- Node: `kscprod-bio1.esr.cri.nz`
- Partition: `prod`
- CPU: AMD EPYC 9374F
- Allocation: exclusive node
- NEXCISION execution: one process pinned to one allowed CPU
- Memory: full node allocation (`--mem=0`)
- Working filesystem: node-local `/tmp` on XFS
- Python: 3.10.14
- Software artifact: `software/nexcision-0.1.0-py3-none-any.whl`

The entire node is reserved to prevent interference from other Slurm jobs, but
NEXCISION is deliberately run on one CPU because v0.1.0 is single-process.

## Cache and timing protocol

1. All inputs are generated on node-local `/tmp`.
2. Generated files are flushed with `sync`.
3. One unreported warm-up run is performed for every configuration.
4. The Linux page cache is **not** dropped.
5. Five measured runs per configuration are executed in a deterministic
   randomized order (`seed=20260722`).
6. Timing covers the NEXCISION subprocess only.
7. Post-run parsing, correctness checks and SHA-256 calculation are outside the
   measured interval.
8. Outputs are deleted after verification.

These are therefore warm-cache, controlled-node application measurements. They
do not estimate cold network-storage performance or durable-write latency.

## Benchmark series

The complete manifest is
[`configs/formal_manifest.tsv`](configs/formal_manifest.tsv).

### A. Input-size scaling — six configurations

- approximately 10 MB
- approximately 100 MB
- approximately 500 MB
- approximately 1 GB
- approximately 2 GB
- approximately 5 GB

All use 512 taxa, 100 disjoint intervals and approximately 10% removal.

### B. Matrix-shape scaling — three configurations

Approximately matched 500 MB matrices:

- many short rows: 64 taxa × 3,500,000 sites;
- balanced: 512 taxa × 500,000 sites;
- fewer wide rows: 8,192 taxa × 32,000 sites.

This separates total bytes from the number and width of matrix rows.

### C. Interval-count scaling — six configurations

A fixed approximately 1 GB matrix is tested with:

- 1 interval;
- 10 intervals;
- 100 intervals;
- 1,000 intervals;
- 10,000 intervals;
- 100,000 intervals.

### D. Interval-geometry scaling — four configurations

A fixed approximately 1 GB matrix and 10,000 submitted intervals are tested as:

- disjoint;
- adjacent;
- partially overlapping;
- nested.

### E. Provenance overhead — two configurations

The same approximately 1 GB matrix is run with and without `--report`.

## Replication

There are 21 configurations:

```text
21 warm-up runs
105 measured runs (21 × 5)
126 total NEXCISION invocations
```

The generated input corpus occupies approximately 22.9 GB (21.3 GiB) before
filtered temporary outputs are considered. The node has approximately 3.5 TB
of local `/tmp` storage.

## Primary outcomes

For each configuration, report the median and interquartile range across five
measured repetitions for:

- elapsed wall-clock time;
- peak resident memory;
- input throughput;
- total CPU time;
- CPU efficiency (`CPU seconds / elapsed seconds`).

All raw repetitions remain available in the measured-results TSV.

## Correctness and determinism requirements

Every measured run must:

- exit successfully;
- retain the expected number of site rows;
- preserve `ntax`;
- update `nchar` correctly;
- create the counts output;
- create the report when requested;
- produce the same filtered-output SHA-256 checksum as all other repetitions of
  that configuration.

A single correctness or determinism failure stops the formal job.

## Execution order

Run the formal-runner smoke test first:

```bash
sbatch experiments/experiment_2_scalability/scripts/run_formal_smoke.slurm
```

After it passes, launch the formal benchmark:

```bash
sbatch experiments/experiment_2_scalability/scripts/run_formal.slurm
```

## Result files

Compact results are copied back to:

```text
experiments/experiment_2_scalability/results/formal/
```

Generated matrices and filtered outputs remain under `/tmp` only and are
removed automatically when the Slurm job exits.

# Experiment 2 — runtime and memory scalability

## Research question

How do NEXCISION runtime, peak memory and throughput scale with input size,
matrix shape, interval count, interval geometry and provenance reporting?

## Why this experiment is separate from Experiment 1

Experiment 1 established correctness. Experiment 2 measures computational
behaviour. Every benchmark output is still checked for correctness, but the
primary outcomes are:

- wall-clock time;
- CPU time;
- peak resident memory;
- input and output throughput;
- output size;
- failure at large scale, if any.

## Frozen software under evaluation

The exact wheel stored in `../../software/` is installed into the benchmark
environment. Its SHA-256 checksum is recorded with every run.

The first implementation under evaluation is NEXCISION v0.1.0. It reads the
complete UTF-8 NEXUS file into memory before filtering. Consequently, the
formal benchmark must not assume bounded-memory streaming; memory behaviour is
an empirical outcome of this experiment.

## Experimental stages

### Stage 2A — instrumentation pilot

Three small matrices are used to verify that:

1. deterministic input generation works;
2. elapsed time, CPU time and peak memory are captured;
3. expected rows are removed exactly;
4. repeated runs are recorded consistently;
5. the scripts work on the intended benchmark machine.

Pilot results are not manuscript performance results.

### Stage 2B — formal benchmark

After the pilot is approved, the final benchmark will separately examine:

1. **Input-size scaling** at a fixed interval count and removal fraction.
2. **Matrix-shape scaling** at approximately matched input sizes.
3. **Interval-count scaling** from 1 to 100,000 intervals.
4. **Interval geometry**: disjoint, adjacent, overlapping and nested.
5. **Provenance overhead**: runs with and without `--report`.

Each formal configuration will be repeated five times in randomized order on a
single controlled machine or reserved compute node.

## Benchmark-machine rules

Formal results must be generated on one documented machine or one fixed HPC
node type. Use local scratch storage rather than a network-mounted home
directory where possible. Record background load and avoid running unrelated
heavy jobs concurrently.

Capture the machine before running any benchmarks:

```bash
python experiments/experiment_2_scalability/scripts/collect_system_info.py \
  --output experiments/experiment_2_scalability/results/system_info.json
```

## Linux/Slurm protocol

The formal benchmark is configured for the fixed PHF Science node
`kscprod-bio1`, using one physical CPU core and node-local `/tmp` storage. See
[`LINUX_SLURM_PROTOCOL.md`](LINUX_SLURM_PROTOCOL.md).

Run the instrumentation pilot from the repository root:

```bash
sbatch experiments/experiment_2_scalability/scripts/run_pilot.slurm
```

The Slurm job creates a clean environment in local scratch, installs the frozen
wheel, records system metadata, executes nine randomized pilot runs, and copies
only compact results back to the repository. GNU `/usr/bin/time` is not required;
timing and peak RSS are collected with Python's standard-library instrumentation.

## Repository policy

Commit:

- generator and runner scripts;
- benchmark manifests;
- system metadata;
- compact result tables;
- summary statistics;
- figure-generation code and final figures.

Do not commit:

- generated large NEXUS matrices;
- filtered benchmark outputs;
- temporary directories;
- repeated raw logs;
- virtual environments.

Frozen raw benchmark outputs should be archived with a release or research-data
deposit if they are required for the manuscript record.

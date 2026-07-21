# Linux/Slurm benchmark protocol

Formal Experiment 2 measurements are generated on one fixed Linux node using
node-local storage. The current benchmark host is:

- node: `kscprod-bio1`
- partition: `prod`
- CPU: AMD EPYC 9374F, 64 physical cores / 128 hardware threads
- memory: approximately 2.2 TiB
- local scratch: `/tmp` on XFS
- Python: 3.10.14

## Controls

1. Use only `kscprod-bio1` for the formal benchmark.
2. Use one physical CPU core (`--hint=nomultithread`).
3. Keep `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and
   `NUMEXPR_NUM_THREADS` fixed at 1.
4. Generate inputs and write outputs under `/tmp`, not the NFS-mounted home
   directory.
5. Use the frozen wheel under `software/` with `--no-deps`.
6. Randomise run order and repeat every formal configuration five times.
7. Request an exclusive node allocation for the final manuscript run if cluster
   policy permits. A shared-node pilot is acceptable only for instrumentation
   checks.
8. Record `system_info.json` from within the allocation.

## Why GNU time is not required

The benchmark runner measures wall time with `time.perf_counter()` and child
process CPU and peak resident memory with Python's standard-library `resource`
module. On Linux, `ru_maxrss` is converted from KiB to bytes. Therefore,
`/usr/bin/time -v` is optional rather than a dependency.

## Pilot submission

From the repository root:

```bash
sbatch experiments/experiment_2_scalability/scripts/run_pilot.slurm
```

The job copies the repository to a unique directory under `/tmp`, creates a
clean virtual environment there, installs the frozen wheel, runs all nine pilot
executions, and copies only compact results back to the repository.

## Formal run

The formal manifest and Slurm script will be frozen only after the pilot has
passed on `kscprod-bio1`. For the final manuscript run, add `#SBATCH --exclusive`
only after confirming that whole-node reservations are acceptable on the
`prod` partition.

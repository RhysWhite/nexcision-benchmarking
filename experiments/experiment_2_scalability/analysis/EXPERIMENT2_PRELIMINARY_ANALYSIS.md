# NEXCISION Experiment 2: preliminary quality control and interpretation

## Status

**PASS — all 105 formal measured executions were correct and all 21 configurations produced deterministic filtered outputs.**

This analysis uses the measured-run table, configuration summary, and system
snapshots from Slurm job `2432330`.

## Benchmark integrity

- Formal measured executions: **105**
- Correct executions: **105/105**
- Configurations: **21**
- Deterministic configurations: **21/21**
- Median runtime coefficient of variation excluding the sub-second 10 MB case:
  **1.08%**
- Maximum runtime coefficient of variation excluding the 10 MB case:
  **1.89%**
- Correlation between randomized run order and normalized runtime:
  **r = -0.018**
- Correlation between pre-run load average and normalized runtime:
  **r = 0.071**

The 10 MB configuration contained one visibly slower sub-second execution and
had a runtime CV of **33.6%**. Its median remains useful, but this point
should not drive regression inference.

System snapshots were taken **14.7 minutes** apart on the
same host. Available memory was effectively unchanged, load remained
approximately one on a 128-thread node, and scratch use increased by
**21.28 GiB**, matching the planned generated corpus.

## 1. Input-size scaling

Runtime increased from **0.104 s** for a
0.010 GiB input to **24.24 s**
for a 4.83 GiB input.

A linear fit to the six median measurements was:

`elapsed seconds = -0.181 + 5.004 × input GiB`

with **R² = 0.9986**. The log-log exponent across inputs of at least
approximately 100 MB was **0.978**, consistent with
near-linear scaling.

Input throughput reached approximately
**223.0 MiB/s** for the 2 GiB configuration and
**203.9 MiB/s** for the 5 GiB configuration.

## 2. Peak-memory scaling

Peak resident memory increased from
**0.063 GiB** to
**23.42 GiB**.

The fitted relationship was:

`peak RSS GiB = 0.017 + 4.849 × input GiB`

with **R² = 0.99999999**.

The current implementation therefore required approximately
**4.85 GiB of peak RSS per GiB of input** under this benchmark
format. This is the main limitation revealed by Experiment 2. NEXCISION v0.1.0
is fast at multi-gigabyte scale, but it is not memory-light: the 4.83 GiB input
required approximately **23.4 GiB**
of peak RSS.

## 3. Matrix shape

The three approximately 500 MB matrices produced markedly different runtimes:

- Tall, many-row matrix: **5.44 s**
- Balanced matrix: **2.25 s**
- Wide, fewer-row matrix: **1.56 s**

The tall matrix was **3.48-fold slower** than the wide matrix,
despite similar total bytes. Peak memory varied much less than runtime.

This indicates that file size alone does not determine performance: the number
of coordinate-labelled rows adds substantial parsing and filtering overhead.

## 4. Number of intervals

Increasing the supplied interval count from 1 to 100,000 increased median
runtime from **4.41 s** to
**5.00 s**, an increase of only
**13.5%**.

Peak memory increased by only **0.8%**. The interval
index therefore scales efficiently even for very large region lists.

## 5. Interval geometry

Across disjoint, adjacent, partially overlapping, and nested sets of 10,000
intervals, median runtimes spanned only
**4.45–4.58 s**,
a spread of **2.8%**.

There is no evidence of a material performance penalty from overlapping or
nested interval structure after preprocessing.

## 6. Provenance reporting

Enabling the deterministic JSON provenance report increased median runtime from
**4.43 s** to
**5.48 s**, an overhead of
**23.6%** for the approximately 1 GiB input.

Peak memory was effectively unchanged. The extra cost is therefore temporal,
not a larger persistent memory footprint.

## Defensible manuscript conclusions

1. **Correctness was maintained at every tested scale.**
2. **Runtime scaled near-linearly with input size**, with a 4.83 GiB input
   processed in approximately 24.2 seconds on one pinned logical CPU of an AMD EPYC 9374F node.
3. **Peak memory scaled linearly**, at approximately 4.85 GiB RSS per GiB of
   input; this is the major current implementation limitation.
4. **The number of site rows matters independently of total bytes.**
5. **Interval count had only modest impact**, even at 100,000 intervals.
6. **Interval geometry had negligible practical effect.**
7. **Provenance reporting imposed a measurable but moderate time cost** without
   increasing peak memory.

## Interpretation boundary

These are controlled, warm-cache measurements on one exclusive Linux node using
node-local XFS storage. They should not be presented as cold-cache,
network-filesystem, laptop, or cross-platform performance estimates.

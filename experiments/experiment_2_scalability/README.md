# Experiment 2 — runtime and memory scalability

## Question

How do NEXCISION runtime, peak memory and throughput scale with matrix size, matrix shape, interval count and interval geometry?

## Planned factors

- taxa/sample columns: 10 to 10,000;
- coordinate-labelled rows: 1,000 to 1,000,000;
- input size: megabytes to multi-gigabyte files;
- intervals: 1 to 100,000;
- disjoint, adjacent, overlapping and nested intervals;
- plain-text and compressed inputs, if compression support is included in the frozen software version.

## Primary outcomes

- wall-clock time;
- CPU time;
- peak resident memory;
- input/output throughput;
- temporary disk use;
- correctness against the independent oracle.

## Repository policy

Commit scripts, benchmark manifests, small summaries and figure-generation code. Do not commit generated large matrices, raw logs or repeated benchmark runs. Archive the frozen raw results with a tagged release or external research-data deposit.

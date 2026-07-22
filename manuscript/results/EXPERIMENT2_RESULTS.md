# Experiment 2 — Scalability and resource use

NEXCISION completed all 105 formally measured executions correctly, and each of
the 21 benchmark configurations produced deterministic filtered outputs across
five randomized repetitions. Excluding the approximately 10 MB configuration,
for which sub-second process-startup noise inflated variability, the median
runtime coefficient of variation across configurations was 1.08%. Normalized
runtime showed no material drift with randomized run order.

Runtime increased near-linearly with input size. Median elapsed time increased
from 0.52 s for an approximately 100 MB matrix to 4.51 s for approximately
1 GB, 8.86 s for approximately 2 GB, and 24.24 s for approximately 5 GB.
A linear model fitted to configuration medians explained 99.86% of runtime
variation. The corresponding log–log scaling exponent for inputs of at least
approximately 100 MB was 0.978, consistent with near-linear scaling.

Peak resident memory also increased linearly with input size. The fitted slope
was approximately 4.85 GiB of peak RSS per GiB of input, with an R² effectively
equal to 1.0. The largest matrix, measuring 4.83 GiB, required approximately
23.4 GiB peak RSS. Thus, although NEXCISION processed multi-gigabyte matrices
rapidly on a single pinned logical CPU, memory consumption was the principal scalability
limitation of version 0.1.0.

Matrix shape influenced runtime independently of file size. Among three
matrices of approximately 500 MB, the tall matrix containing 3.5 million site
rows required 5.44 s, compared with 2.25 s for the balanced matrix and 1.56 s
for the wide matrix containing 32,000 rows. The tall matrix was therefore
3.48-fold slower than the wide matrix, indicating appreciable per-row parsing
and coordinate-evaluation overhead.

Interval handling scaled efficiently. Increasing the exclusion list from one to
100,000 intervals increased median runtime by only 13.5% and peak memory by
0.8%. At a fixed interval count of 10,000, disjoint, adjacent, overlapping and
nested interval sets differed in median runtime by only 2.8%, indicating that
interval geometry had little practical effect after preprocessing.

Generating the deterministic JSON provenance report increased median runtime
from 4.43 s to 5.48 s for the approximately 1 GB configuration, corresponding
to a 23.6% overhead, while peak memory was effectively unchanged. Overall,
NEXCISION maintained exact output correctness at every tested scale, with
near-linear runtime, efficient handling of large interval sets, and predictable
but comparatively high memory requirements.

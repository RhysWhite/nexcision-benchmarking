# Figure 3 legend

**Figure 3. Scalability and resource use of NEXCISION v0.1.0.**

**A,** Median elapsed time versus input-matrix size. Points indicate medians of five randomized measured executions; error bars indicate interquartile ranges (IQR). The teal dashed line is the log–log power-law fit to configuration medians for inputs of approximately 100 MB or larger (exponent 0.978); the smallest ~10 MB input is shown but excluded from this fit because sub-second startup variability is comparatively high. The ordinary linear fit used to calculate the reported original-scale R² is a distinct model and is not overlaid because it predicts a nonpositive runtime at the smallest input. Both axes are logarithmic.

**B,** Median peak resident set size (RSS) versus input size, with IQR error bars. The dashed line is the original-scale linear regression on configuration medians (slope 4.849 GiB RSS per GiB input); both axes are logarithmic.

**C,** Association between matrix shape and runtime at broadly similar input size. Bars indicate medians; error bars indicate IQR. Labels show taxon count × site-row count and actual input size. The three designs varied both the number of taxa and the number of site rows, so this comparison does not isolate row count causally.

**D,** Median runtime as the number of supplied intervals increases from 1 to 100,000 for the same ~0.965 GiB input matrix; error bars indicate IQR. The x-axis is logarithmic, while the y-axis starts at zero. The median runtime increased by 13.5% between the endpoints.

All measurements used the frozen v0.1.0 wheel on one pinned logical CPU of an exclusively allocated AMD EPYC 9374F Linux node with node-local XFS storage. Each of 21 configurations had one unreported warm-up and five randomized measured repetitions; page cache was not cleared. The benchmark's correctness flags evaluated exit status, expected row counts, declared dimensions and output presence; full nucleotide-content comparison was covered separately by Experiment 1. All plotted data are from the archived Experiment 2 records, not a v1.0.0 run.

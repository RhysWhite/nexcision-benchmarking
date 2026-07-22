# Figure 2 legend

**Figure 2. Scalability and resource use of NEXCISION.**

**A,** Median elapsed time as a function of input-matrix size. Points represent
the median of five randomized measured executions and error bars show the
interquartile range. The dashed line shows the linear fit to configuration
medians. Both axes are logarithmic.

**B,** Median peak resident memory as a function of input size. Points represent
configuration medians and error bars show the interquartile range. The dashed
line shows the linear fit. Both axes are logarithmic.

**C,** Effect of matrix shape at broadly similar file size. Matrices differed
in the balance between taxa columns and coordinate-labelled site rows. Bars
show median elapsed time and error bars show the interquartile range across
five measured executions.

**D,** Effect of exclusion-list size on elapsed time for a fixed approximately
1 GiB matrix. Points represent medians and error bars show the interquartile
range. The x-axis is logarithmic.

All formal benchmarks were performed using NEXCISION v0.1.0 on one pinned
logical CPU of an exclusively allocated AMD EPYC 9374F Linux node, with
node-local XFS
storage. One unreported warm-up preceded five measured repetitions for each
configuration, and measured-run order was randomized. Correctness was verified
after every execution.

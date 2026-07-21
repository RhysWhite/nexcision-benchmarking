# Mutation testing

The mutation panel makes twelve deliberate, plausible errors in temporary
copies of `src/nexcision/core.py`. An independent behavioural probe is then run
against each copy.

Examples include exclusive interval boundaries, incorrect dimension updates,
ignored intervals, row reordering, incorrect regional counts, loss of an inline
matrix terminator, and disabled empty-matrix protection.

Run from the repository root:

```bash
python validation/mutation/run_mutation_panel.py
```

A mutant is **killed** when the probe detects the incorrect behaviour and exits
non-zero. The run writes `mutation_results.tsv` and `mutation_summary.json`.

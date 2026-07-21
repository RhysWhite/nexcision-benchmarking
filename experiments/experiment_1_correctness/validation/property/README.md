# Property-based validation

This component uses Hypothesis to generate matrix shapes, row orders, interval
arrangements, command capitalisation, state separators, and terminator styles
independently of the fixed and 1,000-case corpora.

Expected membership uses the direct inclusive rule:

```text
start <= coordinate <= end
```

Run from the repository root:

```bash
python -m pip install '.[validation]'
python validation/property/run_property_tests.py
```

The run writes `property_results.tsv` and `property_summary.json`.

# Safety validation case 012: all sites selected

This case confirms that NEXCISION prevents accidental creation of an empty
matrix.

The input contains six coordinate-labelled rows and the interval `1–1000`
contains all six coordinates.

Expected default behaviour:

- exit code `2`;
- a clear error explains that all rows would be removed;
- no filtered NEXUS, counts, or report file is created.

Expected behaviour with `--allow-empty`:

- all six rows are removed intentionally;
- `ntax` remains `4`;
- `nchar` changes from `6` to `0`;
- the region count is `6`;
- the output and report checksums are valid.

Run the permanent safety cases from the repository root with:

```bash
python validation/run_safety_cases.py
```

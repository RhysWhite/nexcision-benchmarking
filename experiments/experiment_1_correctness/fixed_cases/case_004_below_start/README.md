# Fixed validation 004: coordinate immediately below the start boundary

This case checks that a site immediately outside the lower boundary is retained.

The interval is `180–185`, while the nearest site is:

```text
CP013831_179    G A T C
```

Coordinate `179` is one base below the inclusive start boundary, so no rows
should be removed.

Expected behaviour:

- all six rows are retained in their original order;
- all state strings are unchanged;
- `ntax` remains `4`;
- `nchar` remains `6`;
- the regional removal count is `0`.

Run every permanent case from the repository root with:

```bash
python validation/run_fixed_cases.py
```

# Fixed validation 005: coordinate immediately above the end boundary

This case checks that a site immediately outside the upper boundary is retained.

The interval is `175–180`, while the nearest site is:

```text
CP013831_181    G A T C
```

Coordinate `181` is one base above the inclusive end boundary, so no rows
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

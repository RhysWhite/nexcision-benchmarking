# Fixed validation 002_start_boundary: start boundary

This permanent case checks inclusive interval handling at the start boundary.

The interval `180–185` should remove exactly:

```text
CP013831_180    G A T C
```

The coordinate `180` is exactly on the start boundary of the interval.

Expected behaviour:

- `CP013831_180` is removed;
- all five other rows remain in their original order;
- retained state strings are unchanged;
- `ntax` remains `4`;
- `nchar` changes from `6` to `5`;
- the regional removal count is `1`.

Run every permanent case from the repository root with:

```bash
python validation/run_fixed_cases.py
```

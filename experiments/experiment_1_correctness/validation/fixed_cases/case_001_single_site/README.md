# Fixed validation case 001: single-site interval

This permanent, human-readable case represents a genuine SPANDx-style
transposed NEXUS matrix.

The inclusive interval `175–185` should remove exactly one matrix row:

```text
CP013831_180    G A T C
```

Expected behaviour:

- `CP013831_180` is removed;
- all five other rows are retained in their original order;
- retained state strings are unchanged;
- `ntax` remains `4`;
- `nchar` changes from `6` to `5`;
- the region count is `1`.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py
```

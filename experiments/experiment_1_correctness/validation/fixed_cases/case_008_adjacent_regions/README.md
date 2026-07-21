# Fixed validation case 008: adjacent regions

This case confirms that immediately adjacent input regions are handled
correctly without creating a gap or double-counting any matrix row.

The regions are:

```text
175–185    adjacent_A
186–195    adjacent_B
```

Expected behaviour:

- `CP013831_180` matches `adjacent_A` only;
- `CP013831_190` matches `adjacent_B` only;
- two unique matrix rows are removed;
- each region reports one matching row;
- all four retained rows remain unchanged and in their original order;
- `ntax` remains `4`;
- `nchar` changes from `6` to `4`.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_008_adjacent_regions
```

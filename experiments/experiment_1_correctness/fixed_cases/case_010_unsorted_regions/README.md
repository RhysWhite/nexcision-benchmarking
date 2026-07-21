# Fixed validation case 010: unsorted regions

This case confirms that interval order in the regions file does not affect
filtering and that the regional counts table preserves the submitted order.

The regions are deliberately supplied in this order:

```text
195–205    late_region
155–165    early_region
175–185    middle_region
```

Expected behaviour:

- `CP013831_160`, `CP013831_180`, and `CP013831_200` are removed;
- retained rows remain unchanged and in their original matrix order;
- the counts output remains ordered as `late_region`, `early_region`, then
  `middle_region`;
- `ntax` remains `4`;
- `nchar` changes from `6` to `3`.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_010_unsorted_regions
```

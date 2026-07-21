# Fixed validation case 006: overlapping regions

This case confirms that overlapping input regions are counted independently
while each matching matrix row is removed only once.

The regions are:

```text
175–185    overlap_A
180–195    overlap_B
```

Expected behaviour:

- `CP013831_180` matches both `overlap_A` and `overlap_B`;
- `CP013831_190` matches `overlap_B` only;
- two unique matrix rows are removed;
- `overlap_A` reports one matching row;
- `overlap_B` reports two matching rows;
- all four retained rows remain unchanged and in their original order;
- `ntax` remains `4`;
- `nchar` changes from `6` to `4`.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_006_overlapping_regions
```

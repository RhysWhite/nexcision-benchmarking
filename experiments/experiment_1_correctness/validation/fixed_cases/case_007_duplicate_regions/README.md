# Fixed validation case 007: duplicate regions

This case confirms that listing the same interval twice does not remove a
matrix row more than once, while each input region retains its own count.

The regions are:

```text
175–185    duplicate_A
175–185    duplicate_B
```

Expected behaviour:

- `CP013831_180` matches both duplicate regions;
- only one unique matrix row is removed;
- both `duplicate_A` and `duplicate_B` report one matching row;
- all five retained rows remain unchanged and in their original order;
- `ntax` remains `4`;
- `nchar` changes from `6` to `5`.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_007_duplicate_regions
```

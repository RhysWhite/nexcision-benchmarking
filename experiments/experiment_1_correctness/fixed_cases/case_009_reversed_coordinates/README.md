# Fixed validation case 009: reversed coordinates

This case confirms that region bounds supplied in descending order are safely
normalised before filtering.

The input region is:

```text
185–175    reversed_interval
```

NEXCISION and the independent oracle must treat this as:

```text
175–185    reversed_interval
```

Expected behaviour:

- `CP013831_180` falls within the normalised interval and is removed;
- all five retained rows remain unchanged and in their original order;
- the counts output reports the normalised bounds `175–185`;
- `ntax` remains `4`;
- `nchar` changes from `6` to `5`.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_009_reversed_coordinates
```

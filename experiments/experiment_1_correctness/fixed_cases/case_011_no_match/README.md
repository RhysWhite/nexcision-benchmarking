# Fixed validation case 011: no matching sites

This case confirms that a valid genomic interval containing no observed matrix
coordinates leaves the NEXUS matrix unchanged and reports zero removals.

The input contains coordinates from `160` to `220`, while the supplied interval
is:

```text
1–100    no_match_region
```

Expected behaviour:

- no matrix rows are removed;
- every row and state string remains unchanged and in its original order;
- `ntax` remains `4`;
- `nchar` remains `6`;
- the regional removal count is `0`;
- the filtered NEXUS file is byte-for-byte identical to the input.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_011_no_match
```

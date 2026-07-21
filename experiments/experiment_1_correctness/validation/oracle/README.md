# Independent truth checker

`expected_rows.py` calculates the rows that **should** be removed from a genuine SPANDx-style transposed NEXUS matrix.

It is intentionally separate from NEXCISION:

- it imports no NEXCISION code;
- it does not merge or index intervals;
- it checks each matrix row against every original region using the direct rule `start <= coordinate <= end`.

This implementation is slower by design. Its purpose is correctness, not performance.

## Example

```bash
python validation/oracle/expected_rows.py input.nex regions.tsv \
  --removed expected_removed_rows.tsv \
  --retained expected_retained_rows.tsv \
  --counts expected_region_counts.tsv \
  --summary expected_summary.json
```

The oracle currently targets the genuine SPANDx syntax used in Experiment 1: one complete coordinate-labelled site row per line and a standalone semicolon terminating the matrix.

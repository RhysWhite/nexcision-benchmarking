#!/usr/bin/env python3
"""Verify Figure 1 example against the local, importable NEXCISION package."""
from pathlib import Path
from nexcision.core import Region, filter_nexus_text

root = Path(__file__).resolve().parent
source = (root / 'example_input.nex').read_text(encoding='utf-8')
expected = (root / 'example_expected_filtered.nex').read_text(encoding='utf-8')
rows = [line.strip().split() for line in source.splitlines() if line.strip().startswith('CP013831_')]
assert len(rows) == 5
assert len({len(row[1]) for row in rows}) == 1
assert all(len(row[1]) == 5 for row in rows)
assert all(set(row[1]) <= set('ACGT') for row in rows)
assert rows[0] == ['CP013831_16000', 'AACGT']
assert rows[-1] == ['CP013831_20000', 'AACGT']

observed, counts, result = filter_nexus_text(
    source, [Region(1, 18000, 19000, 'target_interval')]
)
assert observed == expected, 'Filtered file differs from exact expected output'
assert result.matrix_rows_read == 5
assert result.rows_removed == 3
assert result.rows_kept == 2
assert result.dimension_updated == 'nchar'
assert (result.dimension_before,result.dimension_after) == (5,2)
assert result.unparsed_rows == 0
assert '1\ttarget_interval\t18000\t19000\t3' in counts
assert 'DIMENSIONS NTAX=5;' in observed
assert 'TAXLABELS Iso1 Iso2 Iso3 Iso4 Iso5;' in observed
print('PASS: Figure 1 matrix, coordinate membership, exact output, dimensions, and per-region counts')

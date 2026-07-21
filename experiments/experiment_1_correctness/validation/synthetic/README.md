# Synthetic correctness validation

This directory contains the generated component of NEXCISION Experiment 1.
Validation was scaled in three stages: ten small matrices for manual inspection,
a 100-case command-line corpus, and a final 1,000-case formal corpus.

All coordinates, state strings, interval sets, and row orders are deterministic.
The generators use the fixed master seed `20260721`; state values are derived
from SHA-256 of the case identifier, coordinate, and sample-column index.

## Ten-case pilot

The pilot contains small, human-readable matrices spanning ascending,
descending, and shuffled row order; disjoint, overlapping, duplicate, adjacent,
reversed, unsorted, and no-match intervals; and tab- and space-separated state
strings.

```bash
python validation/synthetic/generate_pilot_cases.py
python validation/synthetic/run_pilot_cases.py \
  --results validation/synthetic/pilot_results.tsv \
  --summary validation/synthetic/pilot_summary.json
```

## One-hundred-case command-line corpus

The 100-case corpus spans 2–96 taxa, 20–500 site rows, 1–4 regions, and
0–80% row removal. Each case invokes the independent oracle and the installed
NEXCISION command separately, then repeats NEXCISION to test determinism.

```bash
python validation/synthetic/generate_100_cases.py
python validation/synthetic/run_100_cases.py \
  --tool-python "$(command -v python)" \
  --results validation/synthetic/case_100_results.tsv \
  --summary validation/synthetic/case_100_summary.json
```

## One-thousand-case formal corpus

The final corpus contains ten scenario families with 100 deterministic variants
each. It spans:

- 2–256 taxa/sample columns;
- 20–1,000 coordinate-labelled site rows;
- 1–4 input regions;
- 0–80% row removal;
- ascending, descending, and shuffled row order;
- disjoint, overlapping, nested, duplicate, adjacent, reversed, unsorted, and
  no-match intervals; and
- tab- and space-separated state strings.

The generated corpus is approximately 74 MiB and is deliberately not committed.
Regenerate it with:

```bash
python validation/synthetic/generate_1000_cases.py
```

Run the formal validation from an environment containing the built NEXCISION
wheel:

```bash
python validation/synthetic/run_1000_cases_fast.py \
  --results validation/synthetic/case_1000_results.tsv \
  --summary validation/synthetic/case_1000_summary.json
```

The formal runner loads NEXCISION from the installed wheel and evaluates all
1,000 cases through the public filtering API in one Python process. This avoids
thousands of irrelevant interpreter-startup costs. The 100-case corpus
separately validates the packaged command-line interface.

For every case, the validation checks:

- exact removed-row membership against an independent naive oracle;
- exact retained-row membership and original order;
- unchanged retained state strings;
- preservation of `ntax` and correct reduction of `nchar`;
- per-region counts, including overlaps and duplicates;
- output SHA-256 checksums; and
- byte-identical outputs after a forced repeat run.

Final outputs:

- [`case_1000_manifest.tsv`](case_1000_manifest.tsv)
- [`case_1000_results.tsv`](case_1000_results.tsv)
- [`case_1000_summary.json`](case_1000_summary.json)
- [`case_1000_family_summary.tsv`](case_1000_family_summary.tsv)
- [`case_1000_report.md`](case_1000_report.md)

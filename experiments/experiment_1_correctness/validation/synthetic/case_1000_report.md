# NEXCISION Experiment 1: 1,000-case synthetic validation

## Result

**PASS — 1,000/1,000 deterministic synthetic correctness cases.**

The installed NEXCISION `0.1.0` wheel was evaluated against an independent, deliberately naive interval-membership oracle.

| Measure | Result |
|---|---:|
| Scenario families | 10 |
| Cases | 1,000 |
| Taxa/sample columns | 2–256 |
| Site rows per matrix | 20–1,000 |
| Total site rows evaluated | 304,000 |
| Rows removed | 113,740 |
| Rows retained | 190,260 |
| Input regions per case | 1–4 |
| Removal fraction | 0%–80% |
| Generated corpus size | 73.6 MiB |

Every case passed exact checks for:

- removed-row membership against the independent oracle;
- retained-row membership and original order;
- unchanged retained state strings;
- preservation of `ntax` and correct reduction of `nchar`;
- per-region counts for disjoint, overlapping, nested, duplicate, adjacent, reversed, unsorted, and no-match intervals;
- output SHA-256 checksums; and
- byte-identical outputs after a forced repeat run.

## Reproducibility

The corpus was generated twice from the same fixed specification and produced the same tree digest:

```text
324b4ddbc3d593da089d4e969c6a6eeb710138b182d8328af0844a1443d7b516
```

The generated matrices are not committed because they occupy approximately 73.6 MiB. They can be recreated exactly with:

```bash
python validation/synthetic/generate_1000_cases.py
```

Run the validation from a clean environment containing the built wheel:

```bash
python validation/synthetic/run_1000_cases_fast.py \
  --results validation/synthetic/case_1000_results.tsv \
  --summary validation/synthetic/case_1000_summary.json
```

Tested artifact SHA-256:

```text
e54ed4058f3736a5bc39a79d63dac4e2b43ba62a4a2f3631acc3d749b2ed0ceb  nexcision-0.1.0-py3-none-any.whl
```

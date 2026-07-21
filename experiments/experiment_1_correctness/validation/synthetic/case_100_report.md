# NEXCISION Experiment 1: 100-case synthetic validation

## Result

**PASS — 100/100 deterministic synthetic correctness cases.**

The packaged `nexcision-0.1.0-py3-none-any.whl` was installed in a clean Python
3.13 virtual environment and evaluated independently against the naive oracle.

## Corpus

| Measure | Range or total |
|---|---:|
| Scenario families | 10 |
| Cases per family | 10 |
| Taxa/sample columns | 2–96 |
| Coordinate-labelled site rows per matrix | 20–500 |
| Input regions | 1–4 |
| Removal fraction | 0–80% |
| Total site rows examined | 14,800 |
| Rows removed | 5,600 |
| Rows retained | 9,200 |

The cases included ordinary, disjoint, overlapping, shuffled, descending,
no-match, reversed, duplicate, adjacent, unsorted, nested, and partially
overlapping interval configurations.

## Checks applied to every case

- exact agreement with the independent oracle;
- exact removed-row membership;
- exact retained-row membership and order;
- unchanged retained state strings;
- unchanged `ntax` and correct `nchar` reduction;
- correct per-region counts;
- correct output checksums;
- identical output after a forced repeat run.

All checks passed in all 100 cases.

## Reproducibility

The corpus generator uses master seed `20260721`. Regenerating the complete
corpus produced the same tree digest on two consecutive runs:

```text
7c04983c1042c1474abf7d25428432c2ecd96fb7b15e96801501a1b657929f75
```

Tested wheel SHA-256:

```text
e54ed4058f3736a5bc39a79d63dac4e2b43ba62a4a2f3631acc3d749b2ed0ceb
```

# NEXCISION Experiment 1: formal correctness validation

## Status

**PASS — Experiment 1 is complete.**

The experiment evaluated whether NEXCISION removes exactly the intended
coordinate-labelled rows, preserves all retained matrix information, updates
NEXUS dimensions correctly, reports interval-specific counts accurately,
fails safely on malformed inputs, and behaves deterministically.

## Software evaluated

- Software: NEXCISION
- Version: 0.1.0
- Python: 3.13.5
- Validation date: 21 July 2026
- Primary large-corpus mode: installed wheel through the public core API

## Validation design

Experiment 1 used complementary validation layers rather than relying on a
single test set:

1. Genuine SPANDx matrices established real-world syntax compatibility.
2. An independent naïve oracle calculated expected row membership using the
   direct inclusive rule `start <= coordinate <= end`.
3. Permanent hand-built cases tested boundaries, interval geometry, order,
   formatting, preservation, and empty-output safety.
4. Malformed-input cases tested clean failure and transactional output safety.
5. A deterministic 1,000-case synthetic corpus tested broad combinations of
   matrix size, row order, interval arrangement, and removal fraction.
6. Property-based tests generated additional combinations outside the fixed
   corpus and assessed general invariants.
7. Mutation testing introduced plausible implementation faults and checked
   whether the validation framework detected them.

## Results

| Validation component | Result |
|---|---:|
| Genuine SPANDx matrices | 3 files; 6/6 checks passed |
| Unit tests | 26/26 passed |
| Fixed correctness and preservation cases | 17/17 passed |
| All-sites safety cases | 1/1 passed |
| Malformed-input and output-safety cases | 26/26 passed |
| Deterministic synthetic matrices | 1,000/1,000 passed |
| Property-based invariants | 9/9 passed |
| Configured property-generated examples | 1,800 |
| Deliberate source mutants detected | 12/12 |
| Mutation score | 100% |

### Genuine SPANDx inputs

The real-file checks covered:

- 47 taxa and 266 site rows, generated with SPANDx v4.0.4;
- 237 taxa and 4,649 site rows, generated with SPANDx v3.2;
- 396 taxa and 10,481 site rows, generated with SPANDx v4.0.4.

Single-site and short-interval tests removed exactly the expected rows. Across
all six checks, retained rows and states were unchanged, row order was
preserved, `ntax` remained constant, `nchar` was reduced correctly, and content
following the matrix was preserved.

### Synthetic corpus

The formal corpus contained 1,000 deterministic cases across ten scenario
families. It spanned:

- 2–256 taxa/sample columns;
- 20–1,000 genomic-site rows;
- one to four supplied regions;
- 0–80% row removal;
- ascending, descending, and shuffled rows;
- disjoint, overlapping, nested, adjacent, duplicate, reversed, unsorted, and
  no-match intervals.

In total, NEXCISION evaluated 304,000 site rows. It correctly
removed 113,740 and retained 190,260.
There were no oracle disagreements, altered retained rows, dimension errors,
regional-count errors, checksum errors, or repeat-run differences.

### Property-based testing

Hypothesis 6.158.0 evaluated nine invariants across
1,800 configured generated examples, plus a
fixed duplicate-coordinate regression. The properties covered exact
membership, row-order and state preservation, dimensions, regional counts,
interval-order invariance, idempotence, no-match identity, all-site safety,
duplicate-region invariance, overlap-union equivalence, reversed region-file
normalisation, and custom coordinate regular expressions.

All properties passed.

### Mutation testing

Twelve deliberate faults were introduced into temporary copies of the source.
They included exclusive interval boundaries, incorrect dimension selection,
unsorted or ignored regions, incomplete overlap merging, extraction of the
wrong integer from a label, retained-row reordering, loss of an inline matrix
terminator, disabled empty-matrix protection, and incorrect regional counts.

All 12 mutants were detected; none survived.

## Acceptance criteria

Experiment 1 required 100% correctness for deterministic outputs. All criteria
were met:

- exact removed-row membership;
- exact retained-row membership and ordering;
- unchanged retained state strings;
- correct `ntax` and `nchar` behaviour;
- correct interval-specific counts, including overlaps and duplicates;
- deterministic outputs and report checksums;
- clean rejection of malformed or unsafe operations;
- no unintended partial outputs;
- detection of every deliberate mutant.

## Reproduction

Install validation dependencies and run the lightweight automated suite:

```bash
python -m pip install -r environments/experiment1-requirements.txt
python -m pip install software/nexcision-0.1.0-py3-none-any.whl
python -m unittest discover -s experiments/experiment_1_correctness/software_tests -v
python experiments/experiment_1_correctness/validation/run_fixed_cases.py
python experiments/experiment_1_correctness/validation/run_safety_cases.py
python experiments/experiment_1_correctness/validation/run_invalid_cases.py
python experiments/experiment_1_correctness/validation/property/run_property_tests.py
python experiments/experiment_1_correctness/validation/mutation/run_mutation_panel.py
```

Regenerate and run the full deterministic corpus:

```bash
python experiments/experiment_1_correctness/validation/synthetic/generate_1000_cases.py
python experiments/experiment_1_correctness/validation/synthetic/run_1000_cases_fast.py \
  --results experiments/experiment_1_correctness/validation/synthetic/case_1000_results.tsv \
  --summary experiments/experiment_1_correctness/validation/synthetic/case_1000_summary.json
```

The generated matrices are intentionally not committed because they are fully
reconstructable from the version-controlled generator and manifest.
The regenerated corpus has deterministic tree digest `9ed25d7e2dd4fee380f2f0f32ddcf653694715926905bd54179e7003e64f1c28`.

## Interpretation

Experiment 1 supports the claim that, for the explicitly supported
SPANDx-style transposed NEXUS syntax, NEXCISION performs coordinate-based row
excision exactly, reproducibly, and safely.

This experiment does **not** evaluate runtime or memory scaling at population
scale. Those questions belong to Experiment 2.

# NEXCISION behaviour specification

**Status:** Draft specification for the version evaluated in Experiment 1  
**Coordinate convention:** 1-based, inclusive

This document defines the behaviour that NEXCISION must satisfy during formal correctness validation. It is intentionally narrower than the full NEXUS specification.

## 1. Intended input

NEXCISION is designed primarily for a transposed NEXUS matrix in which:

- each matrix row represents one genomic site;
- each matrix column represents one taxon or sample;
- the first token of each matrix row contains the genomic coordinate;
- the coordinate is the terminal integer following an underscore by default.

Example:

```text
18AR0845_1_14268    A A A G A
```

The coordinate extracted from this row is `14268`.

The default coordinate regular expression is:

```text
_(\d+)$
```

A custom expression may be supplied with `--position-regex`. It must contain exactly one capture group representing a positive integer coordinate.

## 2. Supported NEXUS structure

NEXCISION supports:

- exactly one standalone `MATRIX` line;
- a matrix terminated by a semicolon;
- transposed matrices declared using `FORMAT ... TRANSPOSE;`;
- ordinary non-transposed matrices when deliberately supplied;
- whitespace-separated matrix states, including spaces and tabs;
- blank lines and whole-line NEXUS comments inside the matrix;
- a final matrix row whose terminating semicolon is on the same line;
- quoted or unquoted first tokens when the coordinate pattern still matches.

NEXCISION deliberately does not act as a general-purpose NEXUS parser.

## 3. Regions file

The regions file is whitespace-delimited.

```text
start    end    name
48000    50000  example_region
```

Rules:

- the first two columns are required integer coordinates;
- coordinates must be at least 1;
- coordinates are interpreted as 1-based and inclusive;
- a third region name is optional;
- blank lines and lines beginning with `#` are ignored;
- a header beginning with `start` is ignored;
- reversed boundaries are normalised automatically;
- regions may be unsorted, adjacent, overlapping, nested, or duplicated;
- at least one valid region is required.

## 4. Filtering rule

A coordinate-labelled matrix row is removed exactly when its coordinate satisfies:

```text
region_start <= coordinate <= region_end
```

for at least one supplied region.

Each matching matrix row is removed only once, even when it matches multiple or duplicate regions.

All non-matching matrix rows must remain in their original order with their original textual content unchanged.

## 5. Per-region counts

The counts output contains one row for every original input region, in the same order as supplied.

A removed matrix row contributes once to every region that contains its coordinate. Therefore, when regions overlap, the sum of per-region counts may exceed the number of unique rows removed.

## 6. Dimension handling

With `--update-dimension auto`:

- `nchar` is selected when the preceding `FORMAT` command declares `TRANSPOSE`;
- `ntax` is selected otherwise.

The selected dimension is updated only when its declared value equals the number of matrix rows read before filtering. If the value is missing, duplicated, or inconsistent, NEXCISION leaves it unchanged and emits a warning rather than guessing.

Users may explicitly select:

```text
--update-dimension nchar
--update-dimension ntax
--update-dimension none
```

For genuine transposed SPANDx matrices, filtering site rows must reduce `nchar` while leaving `ntax` unchanged.

## 7. Unparseable matrix rows

By default, a non-comment matrix row that does not match the coordinate pattern is treated as an error.

With `--allow-unparsed`, such rows are preserved unchanged and included in the retained matrix-row count.

## 8. Empty-output safety

By default, NEXCISION refuses to remove every matrix row and exits without writing outputs.

An empty matrix may be produced deliberately with:

```text
--allow-empty
```

## 9. Output safety

NEXCISION must:

- refuse to overwrite an input file;
- require every output path to be different;
- refuse to replace existing outputs unless `--force` is supplied;
- stage all requested outputs before replacing any final destination;
- write each output atomically using a temporary file and rename operation;
- restore pre-existing outputs if a forced multi-file commit fails;
- reject nested output paths and parent paths that are files;
- return a non-zero exit status when filtering cannot be performed safely.

## 10. Reproducibility report

When `--report` is supplied, NEXCISION writes a deterministic JSON report containing:

- software name and version;
- input and output paths;
- SHA-256 checksums;
- run parameters;
- matrix rows read, removed, and retained;
- unparsed-row count;
- dimension update information;
- warnings.

Running the same command with identical paths and inputs must produce identical filtered NEXUS, counts, and report files.

## 11. Preservation guarantee

For supported inputs, the only intended changes to the NEXUS file are:

1. removal of coordinate-labelled rows whose coordinates fall within supplied regions; and
2. update of the appropriate dimension value when it can be done safely.

All retained rows must preserve their original order and state strings. Content following the matrix must remain unchanged.

## 12. Validated real-world syntax

The draft specification has been checked against genuine transposed NEXUS matrices produced by:

- SPANDx v3.2: 237 taxa and 4,649 genomic-site rows;
- SPANDx v4.0.4: 47 taxa and 266 genomic-site rows;
- SPANDx v4.0.4: 396 taxa and 10,481 genomic-site rows.

These pilot checks establish the real-file syntax used to design Experiment 1. They do not replace the forthcoming independent synthetic correctness validation.

## 13. Validated formatting variants

Permanent Experiment 1 cases confirm preservation of:

- whole-line comments and blank lines inside the matrix;
- variable indentation and space-separated states;
- tab-separated states used by genuine SPANDx v4.0.4 matrices;
- mixed NEXUS command capitalisation and spaces around dimension assignments;
- a semicolon appended to the final retained matrix row;
- correct matrix termination when the final inline-terminated row is removed.

For these supported forms, all retained row text and non-target content are
preserved exactly, apart from the required dimension update.

## 14. Malformed-input and failure-safety validation

Permanent Experiment 1 cases verify clean rejection of missing, duplicated,
unterminated, interleaved, and unparseable matrix structures; empty or malformed
region files; invalid coordinate regular expressions; missing and non-UTF-8
inputs; and unsafe output paths.

For all expected failures, NEXCISION must return exit code `2`, write a clear
`ERROR:` message to standard error, leave standard output empty, preserve all
pre-existing files, and create no unintended final or temporary outputs.

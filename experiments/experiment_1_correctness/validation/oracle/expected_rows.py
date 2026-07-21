#!/usr/bin/env python3
"""Independent, deliberately simple truth checker for NEXCISION validation.

This script does not import NEXCISION. It scans a SPANDx-style transposed
NEXUS matrix, extracts the terminal coordinate from each row label, and uses a
naive interval-membership test to calculate which rows should be removed.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


POSITION_PATTERN = re.compile(r"_(\d+)$")


class OracleError(ValueError):
    """Raised when the oracle cannot interpret an input safely."""


@dataclass(frozen=True)
class Region:
    region_id: int
    name: str
    start: int
    end: int


@dataclass(frozen=True)
class MatrixRow:
    label: str
    coordinate: int


def load_regions(path: Path) -> list[Region]:
    """Read 1-based inclusive intervals from a whitespace-delimited file."""

    regions: list[Region] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise OracleError(f"Cannot read regions file '{path}': {exc}") from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        fields = re.split(r"\s+", line)
        if fields[0].lower() == "start":
            continue
        if len(fields) < 2:
            raise OracleError(
                f"Regions line {line_number} must contain start and end."
            )

        try:
            start = int(fields[0])
            end = int(fields[1])
        except ValueError as exc:
            raise OracleError(
                f"Regions line {line_number} contains non-integer coordinates."
            ) from exc

        if start < 1 or end < 1:
            raise OracleError(
                f"Regions line {line_number} contains a coordinate below 1."
            )
        if start > end:
            start, end = end, start

        region_id = len(regions) + 1
        name = fields[2] if len(fields) >= 3 else f"region_{region_id}"
        regions.append(Region(region_id, name, start, end))

    if not regions:
        raise OracleError(f"No regions were found in '{path}'.")
    return regions


def extract_coordinate(label: str) -> int:
    """Extract the terminal integer following the final underscore."""

    match = POSITION_PATTERN.search(label.strip("'\""))
    if match is None:
        raise OracleError(f"Cannot extract a coordinate from row label '{label}'.")

    coordinate = int(match.group(1))
    if coordinate < 1:
        raise OracleError(f"Row label '{label}' contains a coordinate below 1.")
    return coordinate


def load_matrix_rows(path: Path) -> list[MatrixRow]:
    """Read coordinate-labelled rows from one SPANDx-style MATRIX block."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise OracleError(f"Cannot read NEXUS file '{path}': {exc}") from exc

    rows: list[MatrixRow] = []
    in_matrix = False
    matrix_blocks = 0

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()

        if not in_matrix:
            if stripped.lower() == "matrix":
                in_matrix = True
                matrix_blocks += 1
            continue

        before, separator, _after = raw_line.partition(";")
        content = before.strip() if separator else stripped

        if not content or content.startswith("["):
            if separator:
                in_matrix = False
            continue

        # The oracle independently supports one complete site row per line,
        # with either a standalone terminator or a semicolon appended to the
        # final matrix row.
        label = content.split(maxsplit=1)[0].strip("'\"")
        coordinate = extract_coordinate(label)
        rows.append(MatrixRow(label, coordinate))

        if separator:
            in_matrix = False

    if in_matrix:
        raise OracleError("The MATRIX block is not terminated by ';'.")
    if matrix_blocks != 1:
        raise OracleError(
            f"Expected exactly one MATRIX block, found {matrix_blocks}."
        )
    if not rows:
        raise OracleError("No coordinate-labelled matrix rows were found.")

    return rows


def row_matches_region(row: MatrixRow, region: Region) -> bool:
    """Return True when a row coordinate lies in one inclusive interval."""

    return region.start <= row.coordinate <= region.end


def should_remove(row: MatrixRow, regions: list[Region]) -> bool:
    """Naive truth rule: remove a row if any original region contains it."""

    return any(row_matches_region(row, region) for region in regions)


def write_rows(path: Path, rows: list[MatrixRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["row_label", "coordinate"])
        for row in rows:
            writer.writerow([row.label, row.coordinate])


def write_counts(path: Path, regions: list[Region], removed: list[MatrixRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(
            ["region_id", "region_name", "start", "end", "expected_removed_rows"]
        )
        for region in regions:
            count = sum(row_matches_region(row, region) for row in removed)
            writer.writerow(
                [region.region_id, region.name, region.start, region.end, count]
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate the expected rows removed by NEXCISION using an "
            "independent naive interval-membership implementation."
        )
    )
    parser.add_argument("nexus", type=Path)
    parser.add_argument("regions", type=Path)
    parser.add_argument("--removed", type=Path, required=True)
    parser.add_argument("--retained", type=Path, required=True)
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        regions = load_regions(args.regions)
        rows = load_matrix_rows(args.nexus)
    except OracleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    removed = [row for row in rows if should_remove(row, regions)]
    retained = [row for row in rows if not should_remove(row, regions)]

    write_rows(args.removed, removed)
    write_rows(args.retained, retained)
    write_counts(args.counts, regions, removed)

    summary = {
        "matrix_rows_read": len(rows),
        "expected_rows_removed": len(removed),
        "expected_rows_retained": len(retained),
        "regions_loaded": len(regions),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Matrix rows read: {len(rows)}")
    print(f"Expected rows removed: {len(removed)}")
    print(f"Expected rows retained: {len(retained)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

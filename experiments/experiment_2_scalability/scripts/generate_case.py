#!/usr/bin/env python3
"""Generate one deterministic transposed NEXUS benchmark case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SYMBOLS = "ACGT"


def state(row_index: int, column_index: int) -> str:
    """Return a deterministic state without costly random-number generation."""
    return SYMBOLS[(row_index * 7 + column_index * 11) % len(SYMBOLS)]


def selected_indices(sites: int, removal_fraction: float) -> list[int]:
    count = max(1, min(sites - 1, round(sites * removal_fraction)))
    start = (sites - count) // 2
    return list(range(start, start + count))


def split_contiguous(indices: list[int], groups: int) -> list[list[int]]:
    groups = max(1, min(groups, len(indices)))
    chunks: list[list[int]] = []
    for group in range(groups):
        left = round(group * len(indices) / groups)
        right = round((group + 1) * len(indices) / groups)
        if right > left:
            chunks.append(indices[left:right])
    return chunks


def build_intervals(
    coordinates: list[int],
    intervals: int,
    geometry: str,
    removal_fraction: float,
) -> list[tuple[int, int, str]]:
    targets = selected_indices(len(coordinates), removal_fraction)
    chunks = split_contiguous(targets, intervals)
    result: list[tuple[int, int, str]] = []

    for index, chunk in enumerate(chunks, start=1):
        start = coordinates[chunk[0]]
        end = coordinates[chunk[-1]]
        result.append((start, end, f"region_{index}"))

    if geometry == "disjoint":
        return result
    if geometry == "adjacent":
        # The deterministic coordinate spacing creates adjacent index ranges.
        return result
    if geometry == "overlapping":
        overlap: list[tuple[int, int, str]] = []
        padding = 14
        for start, end, name in result:
            overlap.append((max(1, start - padding), end + padding, name))
        return overlap
    if geometry == "nested":
        outer_start = coordinates[targets[0]]
        outer_end = coordinates[targets[-1]]
        nested = [(outer_start, outer_end, "outer_region")]
        inner_count = max(0, intervals - 1)
        inner_chunks = split_contiguous(targets, inner_count) if inner_count else []
        nested.extend(
            (coordinates[chunk[0]], coordinates[chunk[-1]], f"inner_{i}")
            for i, chunk in enumerate(inner_chunks, start=1)
        )
        return nested
    raise ValueError(f"Unsupported geometry: {geometry}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--taxa", type=int, required=True)
    parser.add_argument("--sites", type=int, required=True)
    parser.add_argument("--intervals", type=int, required=True)
    parser.add_argument(
        "--geometry",
        choices=("disjoint", "adjacent", "overlapping", "nested"),
        required=True,
    )
    parser.add_argument("--removal-fraction", type=float, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.taxa < 2:
        parser.error("--taxa must be at least 2")
    if args.sites < 2:
        parser.error("--sites must be at least 2")
    if args.intervals < 1:
        parser.error("--intervals must be at least 1")
    if not 0 < args.removal_fraction < 1:
        parser.error("--removal-fraction must be between 0 and 1")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    nexus = output_dir / "input.nex"
    regions_path = output_dir / "regions.tsv"
    metadata_path = output_dir / "case.json"

    coordinate_start = 100
    coordinate_step = 7
    coordinates = [coordinate_start + i * coordinate_step for i in range(args.sites)]
    intervals = build_intervals(
        coordinates,
        args.intervals,
        args.geometry,
        args.removal_fraction,
    )

    removed = [
        coordinate
        for coordinate in coordinates
        if any(start <= coordinate <= end for start, end, _ in intervals)
    ]

    with nexus.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("#NEXUS\n\nbegin data;\n")
        handle.write(f"dimensions ntax={args.taxa} nchar={args.sites};\n")
        handle.write('format datatype=dna symbols="ACGT" gap=. transpose;\n')
        handle.write("taxlabels\n")
        for taxon in range(args.taxa):
            handle.write(f"    sample_{taxon + 1:05d}\n")
        handle.write(";\nmatrix\n")
        for row_index, coordinate in enumerate(coordinates):
            sequence = "\t".join(
                state(row_index, column_index)
                for column_index in range(args.taxa)
            )
            handle.write(f"REF_{coordinate}\t{sequence}\n")
        handle.write(";\nend;\n")

    with regions_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("start\tend\tname\n")
        for start, end, name in intervals:
            handle.write(f"{start}\t{end}\t{name}\n")

    metadata = {
        "case_id": args.case_id,
        "taxa": args.taxa,
        "sites": args.sites,
        "requested_intervals": args.intervals,
        "actual_intervals": len(intervals),
        "geometry": args.geometry,
        "requested_removal_fraction": args.removal_fraction,
        "expected_removed_rows": len(removed),
        "expected_retained_rows": args.sites - len(removed),
        "actual_removal_fraction": len(removed) / args.sites,
        "input_bytes": nexus.stat().st_size,
        "regions_bytes": regions_path.stat().st_size,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

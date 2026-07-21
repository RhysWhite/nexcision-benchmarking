#!/usr/bin/env python3
"""Property-based validation for NEXCISION Experiment 1."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from hypothesis import HealthCheck, __version__ as hypothesis_version, assume, given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[2]

from nexcision import NexusFilterError, Region, filter_nexus_text, load_regions  # noqa: E402
from nexcision import __version__ as nexcision_version  # noqa: E402

HERE = Path(__file__).resolve().parent
SYMBOLS = "01?-"


@dataclass(frozen=True)
class MatrixCase:
    ntax: int
    coordinates: tuple[int, ...]
    intervals: tuple[tuple[int, int], ...]
    separator: str
    command_case: str
    inline_terminator: bool


def states(row: int, coordinate: int, ntax: int, separator: str) -> str:
    return separator.join(
        SYMBOLS[(coordinate + row * 3 + column * 5) % len(SYMBOLS)]
        for column in range(ntax)
    )


def build_nexus(
    ntax: int,
    coordinates: tuple[int, ...] | list[int],
    *,
    separator: str = "\t",
    command_case: str = "mixed",
    inline_terminator: bool = False,
    label_factory: Callable[[int], str] | None = None,
) -> tuple[str, list[tuple[str, str]]]:
    label_factory = label_factory or (lambda coordinate: f"REF_{coordinate}")
    forms = {
        "lower": ("begin data;", "dimensions", "format", "taxlabels", "matrix", "end;"),
        "upper": ("BEGIN DATA;", "DIMENSIONS", "FORMAT", "TAXLABELS", "MATRIX", "END;"),
        "mixed": ("Begin data;", "Dimensions", "Format", "Taxlabels", "Matrix", "End;"),
    }
    begin, dimensions, fmt, taxlabels, matrix, end = forms[command_case]
    lines = [
        "#NEXUS\n",
        f"{begin}\n",
        f"{dimensions} ntax={ntax} nchar={len(coordinates)};\n",
        f'{fmt} datatype=standard symbols="01?-" gap=- transpose;\n',
        f"{taxlabels} " + " ".join(f"sample_{i + 1}" for i in range(ntax)) + ";\n",
        f"{matrix}\n",
    ]
    rows: list[tuple[str, str]] = []
    for row_index, coordinate in enumerate(coordinates):
        label = label_factory(coordinate)
        state_text = states(row_index, coordinate, ntax, separator)
        rows.append((label, state_text))
        terminator = ";" if inline_terminator and row_index == len(coordinates) - 1 else ""
        lines.append(f"    {label}{separator}{state_text}{terminator}\n")
    if not inline_terminator:
        lines.append(";\n")
    lines.append(f"{end}\n")
    return "".join(lines), rows


def parse_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    in_matrix = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not in_matrix:
            if stripped.lower() == "matrix":
                in_matrix = True
            continue
        before, separator, _after = raw.partition(";")
        content = before.strip() if separator else stripped
        if content and not content.startswith("["):
            fields = content.split(maxsplit=1)
            assert len(fields) == 2, f"Malformed row: {content!r}"
            rows.append((fields[0].strip("'\""), fields[1]))
        if separator:
            in_matrix = False
    return rows


def dimensions(text: str) -> tuple[int, int]:
    match = re.search(
        r"\bdimensions\b[^;]*\bntax\s*=\s*(\d+)[^;]*\bnchar\s*=\s*(\d+)",
        text,
        flags=re.I | re.S,
    )
    assert match is not None
    return int(match.group(1)), int(match.group(2))


def counts(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(text.splitlines(), delimiter="\t"))


def normalise(interval: tuple[int, int]) -> tuple[int, int]:
    a, b = interval
    return (a, b) if a <= b else (b, a)


def expected_remove(coordinate: int, intervals: tuple[tuple[int, int], ...] | list[tuple[int, int]]) -> bool:
    return any(start <= coordinate <= end for start, end in map(normalise, intervals))


def regions(intervals: tuple[tuple[int, int], ...] | list[tuple[int, int]]) -> list[Region]:
    return [Region(i, *normalise(interval), f"region_{i}") for i, interval in enumerate(intervals, 1)]


@st.composite
def matrix_cases(draw: st.DrawFn) -> MatrixCase:
    return MatrixCase(
        ntax=draw(st.integers(1, 24)),
        coordinates=tuple(draw(st.lists(st.integers(1, 10_000), min_size=1, max_size=45, unique=True))),
        intervals=tuple(draw(st.lists(st.tuples(st.integers(1, 10_000), st.integers(1, 10_000)), min_size=1, max_size=10))),
        separator=draw(st.sampled_from(["\t", " "])),
        command_case=draw(st.sampled_from(["mixed", "lower", "upper"])),
        inline_terminator=draw(st.booleans()),
    )


PROPERTIES: list[tuple[str, int, Callable[[], None]]] = []


def property_case(name: str, examples: int):
    def decorate(function: Callable[[], None]) -> Callable[[], None]:
        PROPERTIES.append((name, examples, function))
        return function
    return decorate


@property_case("membership_order_states_dimensions_and_counts", 500)
@settings(max_examples=500, derandomize=True, database=None, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(matrix_cases())
def core_invariants(case: MatrixCase) -> None:
    text, original = build_nexus(
        case.ntax,
        case.coordinates,
        separator=case.separator,
        command_case=case.command_case,
        inline_terminator=case.inline_terminator,
    )
    region_list = regions(case.intervals)
    filtered, count_text, result = filter_nexus_text(text, region_list, allow_empty=True)
    expected_rows = [row for coordinate, row in zip(case.coordinates, original, strict=True) if not expected_remove(coordinate, case.intervals)]
    removed_coordinates = [coordinate for coordinate in case.coordinates if expected_remove(coordinate, case.intervals)]
    assert parse_rows(filtered) == expected_rows
    assert dimensions(filtered) == (case.ntax, len(expected_rows))
    assert result.matrix_rows_read == len(case.coordinates)
    assert result.rows_removed == len(removed_coordinates)
    assert result.rows_kept == len(expected_rows)
    assert result.dimension_updated == "nchar"
    observed = counts(count_text)
    assert len(observed) == len(region_list)
    for row, region in zip(observed, region_list, strict=True):
        expected_count = sum(region.start <= coordinate <= region.end for coordinate in removed_coordinates)
        assert int(row["removed_rows"]) == expected_count


@property_case("interval_order_invariance", 200)
@settings(max_examples=200, derandomize=True, database=None, deadline=None)
@given(matrix_cases())
def interval_order_invariance(case: MatrixCase) -> None:
    text, _ = build_nexus(case.ntax, case.coordinates)
    region_list = regions(case.intervals)
    forward = filter_nexus_text(text, region_list, allow_empty=True)
    reverse = filter_nexus_text(text, list(reversed(region_list)), allow_empty=True)
    assert forward[0] == reverse[0]
    assert forward[2].rows_removed == reverse[2].rows_removed


@property_case("idempotence", 200)
@settings(max_examples=200, derandomize=True, database=None, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
@given(matrix_cases())
def idempotence(case: MatrixCase) -> None:
    kept = [c for c in case.coordinates if not expected_remove(c, case.intervals)]
    assume(kept)
    text, _ = build_nexus(case.ntax, case.coordinates)
    region_list = regions(case.intervals)
    once = filter_nexus_text(text, region_list)[0]
    twice, _counts, result = filter_nexus_text(once, region_list)
    assert twice == once
    assert result.rows_removed == 0


@property_case("no_match_identity", 150)
@settings(max_examples=150, derandomize=True, database=None, deadline=None)
@given(st.integers(1, 24), st.lists(st.integers(1, 10_000), min_size=1, max_size=50, unique=True))
def no_match_identity(ntax: int, coordinates: list[int]) -> None:
    text, _ = build_nexus(ntax, coordinates)
    start = max(coordinates) + 1
    filtered, count_text, result = filter_nexus_text(text, [Region(1, start, start + 100, "outside")])
    assert filtered == text
    assert result.rows_removed == 0
    assert int(counts(count_text)[0]["removed_rows"]) == 0


@property_case("full_overlap_safety_and_override", 100)
@settings(max_examples=100, derandomize=True, database=None, deadline=None)
@given(st.integers(1, 24), st.lists(st.integers(1, 10_000), min_size=1, max_size=50, unique=True))
def full_overlap(ntax: int, coordinates: list[int]) -> None:
    text, _ = build_nexus(ntax, coordinates)
    region_list = [Region(1, 1, max(coordinates), "all")]
    try:
        filter_nexus_text(text, region_list)
    except NexusFilterError as exc:
        assert "remove all" in str(exc)
    else:
        raise AssertionError("All-sites safety did not trigger")
    filtered, count_text, result = filter_nexus_text(text, region_list, allow_empty=True)
    assert parse_rows(filtered) == []
    assert dimensions(filtered) == (ntax, 0)
    assert result.rows_removed == len(coordinates)
    assert int(counts(count_text)[0]["removed_rows"]) == len(coordinates)


@property_case("duplicate_region_output_invariance", 150)
@settings(max_examples=150, derandomize=True, database=None, deadline=None)
@given(matrix_cases())
def duplicate_region(case: MatrixCase) -> None:
    text, _ = build_nexus(case.ntax, case.coordinates)
    first = regions(case.intervals[:1])[0]
    single = filter_nexus_text(text, [first], allow_empty=True)
    duplicated = filter_nexus_text(text, [first, Region(2, first.start, first.end, "duplicate")], allow_empty=True)
    assert single[0] == duplicated[0]
    count_rows = counts(duplicated[1])
    assert count_rows[0]["removed_rows"] == count_rows[1]["removed_rows"]


@property_case("overlap_union_output_invariance", 200)
@settings(max_examples=200, derandomize=True, database=None, deadline=None)
@given(
    st.integers(1, 24),
    st.lists(st.integers(1, 10_000), min_size=1, max_size=50, unique=True),
    st.integers(1, 9_000),
    st.integers(1, 500),
    st.integers(0, 500),
)
def overlap_union(ntax: int, coordinates: list[int], start: int, width: int, overlap: int) -> None:
    overlap = min(overlap, width)
    first = (start, start + width)
    second_start = max(1, start + width - overlap)
    second = (second_start, second_start + width)
    union = (min(first[0], second[0]), max(first[1], second[1]))
    text, _ = build_nexus(ntax, coordinates)
    split = filter_nexus_text(text, regions([first, second]), allow_empty=True)
    combined = filter_nexus_text(text, regions([union]), allow_empty=True)
    assert split[0] == combined[0]
    assert split[2].rows_removed == combined[2].rows_removed


@property_case("reversed_region_file_normalisation", 150)
@settings(max_examples=150, derandomize=True, database=None, deadline=None)
@given(st.integers(1, 10_000), st.integers(1, 10_000))
def reversed_loading(a: int, b: int) -> None:
    with tempfile.TemporaryDirectory(prefix="nexcision-property-") as directory:
        path = Path(directory) / "regions.tsv"
        path.write_text(f"start\tend\tname\n{a}\t{b}\tregion\n", encoding="utf-8")
        loaded = load_regions(path)
    assert loaded[0].start == min(a, b)
    assert loaded[0].end == max(a, b)


@property_case("custom_coordinate_regex", 150)
@settings(max_examples=150, derandomize=True, database=None, deadline=None)
@given(
    st.integers(1, 24),
    st.lists(st.integers(1, 10_000), min_size=1, max_size=40, unique=True),
    st.integers(0, 1_000),
)
def custom_regex(ntax: int, coordinates: list[int], prefix: int) -> None:
    text, original = build_nexus(ntax, coordinates, label_factory=lambda coordinate: f"sample{prefix}_pos{coordinate}")
    chosen = coordinates[0]
    filtered, _counts, result = filter_nexus_text(
        text,
        [Region(1, chosen, chosen, "chosen")],
        position_pattern=r"_pos(\d+)$",
        allow_empty=True,
    )
    expected = [row for coordinate, row in zip(coordinates, original, strict=True) if coordinate != chosen]
    assert parse_rows(filtered) == expected
    assert result.rows_removed == 1


def duplicate_coordinate_regression() -> None:
    text = """#NEXUS
Begin data;
Dimensions ntax=2 nchar=3;
Format datatype=standard symbols="01" gap=- transpose;
Taxlabels A B;
Matrix
    first_100 0 1
    second_100 1 0
    third_200 1 1
;
End;
"""
    filtered, count_text, result = filter_nexus_text(text, [Region(1, 100, 100, "duplicate")])
    assert result.rows_removed == 2
    assert parse_rows(filtered) == [("third_200", "1 1")]
    assert int(counts(count_text)[0]["removed_rows"]) == 2


def write_results(rows: list[dict[str, object]], elapsed: float, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "property_results.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["property", "configured_examples", "status", "runtime_seconds"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "properties": len(rows),
        "properties_passed": sum(row["status"] == "PASS" for row in rows),
        "configured_generated_examples": sum(int(row["configured_examples"]) for row in rows),
        "fixed_regressions": 1,
        "fixed_regressions_passed": 1,
        "wall_seconds": elapsed,
        "hypothesis_version": hypothesis_version,
        "nexcision_version": nexcision_version,
        "deterministic_generation": True,
        "hypothesis_database_disabled": True,
    }
    (output_dir / "property_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args(argv)
    output_dir = args.output_dir.resolve()
    started = time.perf_counter()
    rows: list[dict[str, object]] = []
    for name, examples, function in PROPERTIES:
        test_started = time.perf_counter()
        try:
            function()
        except Exception as exc:
            rows.append({"property": name, "configured_examples": examples, "status": "FAIL", "runtime_seconds": f"{time.perf_counter() - test_started:.6f}"})
            write_results(rows, time.perf_counter() - started, output_dir)
            print(f"FAIL — {name}: {exc}", file=sys.stderr)
            return 1
        rows.append({"property": name, "configured_examples": examples, "status": "PASS", "runtime_seconds": f"{time.perf_counter() - test_started:.6f}"})
        print(f"PASS — {name} ({examples} generated examples)")
    duplicate_coordinate_regression()
    print("PASS — duplicate_coordinate_regression")
    elapsed = time.perf_counter() - started
    write_results(rows, elapsed, output_dir)
    print(f"PASS — all {len(rows)} properties ({sum(examples for _name, examples, _function in PROPERTIES)} configured generated examples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

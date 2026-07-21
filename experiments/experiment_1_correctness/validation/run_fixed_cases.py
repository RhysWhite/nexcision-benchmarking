#!/usr/bin/env python3
"""Run all permanent NEXCISION fixed validation cases.

Each case is checked twice:
1. An independent, deliberately simple oracle calculates the expected result.
2. NEXCISION is run through its command-line interface.

Both outputs must match the checked-in truth files exactly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path


class ValidationError(RuntimeError):
    """Raised when a fixed validation case does not pass."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        rendered = " ".join(command)
        raise ValidationError(
            f"Command failed with exit code {completed.returncode}: {rendered}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_matrix_rows(path: Path) -> list[tuple[str, str]]:
    """Parse the standalone or inline terminator syntax used by fixed cases."""

    rows: list[tuple[str, str]] = []
    in_matrix = False
    matrix_blocks = 0

    for raw_line in path.read_text(encoding="utf-8").splitlines():
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

        fields = content.split(maxsplit=1)
        if len(fields) != 2:
            raise ValidationError(f"Malformed matrix row in {path}: {content!r}")
        rows.append((fields[0].strip("'\""), fields[1]))

        if separator:
            in_matrix = False

    if in_matrix:
        raise ValidationError(f"Unterminated MATRIX block in {path}")
    if matrix_blocks != 1:
        raise ValidationError(
            f"Expected one MATRIX block in {path}, found {matrix_blocks}"
        )
    return rows


def parse_dimensions(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"\bdimensions\b[^;]*\bntax\s*=\s*(\d+)[^;]*\bnchar\s*=\s*(\d+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise ValidationError(f"Could not read ntax/nchar from {path}")
    return int(match.group(1)), int(match.group(2))


def removed_rows(
    original: list[tuple[str, str]], filtered: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    """Return original rows absent from filtered output while preserving order."""

    retained_counts = Counter(filtered)
    removed: list[tuple[str, str]] = []
    for row in original:
        if retained_counts[row] > 0:
            retained_counts[row] -= 1
        else:
            removed.append(row)
    return removed


def compare_bytes(observed: Path, expected: Path, description: str) -> None:
    if observed.read_bytes() != expected.read_bytes():
        raise ValidationError(
            f"{description} differs from the checked-in expected file:\n"
            f"  observed: {observed}\n  expected: {expected}"
        )


def validate_report(
    report_path: Path,
    output_path: Path,
    counts_path: Path,
    summary: dict[str, int],
    original_nchar: int,
) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    results = report["results"]
    rows_removed = summary["expected_rows_removed"]
    rows_retained = summary["expected_rows_retained"]

    expected_results = {
        "regions_loaded": summary["regions_loaded"],
        "matrix_rows_read": summary["matrix_rows_read"],
        "rows_removed": rows_removed,
        "rows_kept": rows_retained,
        "unparsed_rows": 0,
        "dimension_updated": "nchar",
        "dimension_before": original_nchar,
        "dimension_after": original_nchar - rows_removed,
        "warnings": [],
    }
    for key, expected in expected_results.items():
        if results.get(key) != expected:
            raise ValidationError(
                f"Report field results.{key} is {results.get(key)!r}; "
                f"expected {expected!r}."
            )

    recorded_output = report["outputs"]["filtered_nexus"]["sha256"]
    recorded_counts = report["outputs"]["region_counts"]["sha256"]
    if recorded_output != sha256(output_path):
        raise ValidationError("Filtered-output checksum in report is incorrect.")
    if recorded_counts != sha256(counts_path):
        raise ValidationError("Counts checksum in report is incorrect.")


def validate_case(
    case_dir: Path,
    work_dir: Path,
    oracle: Path,
    repo_root: Path,
) -> tuple[str, list[str]]:
    input_nexus = case_dir / "input.nex"
    regions = case_dir / "regions.tsv"
    summary_path = case_dir / "expected_summary.json"

    required = [
        input_nexus,
        regions,
        summary_path,
        case_dir / "expected_filtered.nex",
        case_dir / "expected_removed.tsv",
        case_dir / "expected_retained.tsv",
        case_dir / "expected_oracle_counts.tsv",
        case_dir / "expected_nexcision_counts.tsv",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise ValidationError(f"Missing required case files: {missing}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    case_work = work_dir / case_dir.name
    oracle_dir = case_work / "oracle"
    nexcision_dir = case_work / "nexcision"
    oracle_dir.mkdir(parents=True, exist_ok=True)
    nexcision_dir.mkdir(parents=True, exist_ok=True)

    oracle_removed = oracle_dir / "removed.tsv"
    oracle_retained = oracle_dir / "retained.tsv"
    oracle_counts = oracle_dir / "counts.tsv"
    oracle_summary = oracle_dir / "summary.json"

    run_command(
        [
            sys.executable,
            str(oracle),
            str(input_nexus),
            str(regions),
            "--removed",
            str(oracle_removed),
            "--retained",
            str(oracle_retained),
            "--counts",
            str(oracle_counts),
            "--summary",
            str(oracle_summary),
        ]
    )

    compare_bytes(oracle_removed, case_dir / "expected_removed.tsv", "Oracle removed rows")
    compare_bytes(oracle_retained, case_dir / "expected_retained.tsv", "Oracle retained rows")
    compare_bytes(oracle_counts, case_dir / "expected_oracle_counts.tsv", "Oracle counts")
    compare_bytes(oracle_summary, summary_path, "Oracle summary")

    output_nexus = nexcision_dir / "filtered.nex"
    output_counts = nexcision_dir / "counts.tsv"
    output_report = nexcision_dir / "report.json"

    env = os.environ.copy()
    source_dir = str(repo_root / "src")
    env["PYTHONPATH"] = (
        source_dir
        if not env.get("PYTHONPATH")
        else source_dir + os.pathsep + env["PYTHONPATH"]
    )

    run_command(
        [
            sys.executable,
            "-m",
            "nexcision",
            str(input_nexus),
            str(regions),
            "--output",
            str(output_nexus),
            "--counts",
            str(output_counts),
            "--report",
            str(output_report),
        ],
        env=env,
    )

    compare_bytes(output_nexus, case_dir / "expected_filtered.nex", "Filtered NEXUS")
    compare_bytes(output_counts, case_dir / "expected_nexcision_counts.tsv", "NEXCISION counts")

    original_rows = parse_matrix_rows(input_nexus)
    filtered_rows = parse_matrix_rows(output_nexus)
    observed_removed = removed_rows(original_rows, filtered_rows)

    expected_removed_labels = [row["row_label"] for row in read_tsv(oracle_removed)]
    expected_retained_labels = [row["row_label"] for row in read_tsv(oracle_retained)]
    observed_removed_labels = [label for label, _ in observed_removed]
    observed_retained_labels = [label for label, _ in filtered_rows]

    if observed_removed_labels != expected_removed_labels:
        raise ValidationError(
            "NEXCISION removed rows do not match the oracle.\n"
            f"  observed: {observed_removed_labels}\n"
            f"  expected: {expected_removed_labels}"
        )
    if observed_retained_labels != expected_retained_labels:
        raise ValidationError(
            "NEXCISION retained rows or their order do not match the oracle.\n"
            f"  observed: {observed_retained_labels}\n"
            f"  expected: {expected_retained_labels}"
        )

    # Comparing complete row tuples proves that every retained state string is unchanged.
    retained_counts = Counter(filtered_rows)
    expected_retained_tuples: list[tuple[str, str]] = []
    for row in original_rows:
        if retained_counts[row] > 0:
            retained_counts[row] -= 1
            expected_retained_tuples.append(row)
    if filtered_rows != expected_retained_tuples:
        raise ValidationError("Retained row labels, order, or state strings changed.")

    original_ntax, original_nchar = parse_dimensions(input_nexus)
    filtered_ntax, filtered_nchar = parse_dimensions(output_nexus)
    if filtered_ntax != original_ntax:
        raise ValidationError(
            f"ntax changed from {original_ntax} to {filtered_ntax}; it must be preserved."
        )
    if filtered_nchar != summary["expected_rows_retained"]:
        raise ValidationError(
            f"nchar is {filtered_nchar}; expected {summary['expected_rows_retained']}."
        )

    oracle_counts_rows = read_tsv(oracle_counts)
    nexcision_counts_rows = read_tsv(output_counts)
    oracle_values = [int(row["expected_removed_rows"]) for row in oracle_counts_rows]
    nexcision_values = [int(row["removed_rows"]) for row in nexcision_counts_rows]
    if nexcision_values != oracle_values:
        raise ValidationError(
            f"Region counts differ: NEXCISION={nexcision_values}, oracle={oracle_values}."
        )

    validate_report(
        output_report,
        output_nexus,
        output_counts,
        summary,
        original_nchar,
    )

    return case_dir.name, observed_removed_labels


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run every permanent NEXCISION fixed validation case."
    )
    parser.add_argument(
        "--case",
        help="Run only one case directory name, for example case_002_start_boundary.",
    )
    parser.add_argument(
        "--keep-output",
        type=Path,
        help="Copy generated outputs to this directory after a successful run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    validation_root = repo_root / "validation"
    fixed_cases_root = validation_root / "fixed_cases"
    oracle = validation_root / "oracle" / "expected_rows.py"

    case_dirs = sorted(path for path in fixed_cases_root.iterdir() if path.is_dir())
    if args.case is not None:
        case_dirs = [path for path in case_dirs if path.name == args.case]
        if not case_dirs:
            print(f"FAIL — unknown fixed case: {args.case}", file=sys.stderr)
            return 1

    try:
        with tempfile.TemporaryDirectory(prefix="nexcision-fixed-cases-") as temp:
            work_dir = Path(temp)
            outcomes = [
                validate_case(case_dir, work_dir, oracle, repo_root)
                for case_dir in case_dirs
            ]
            if args.keep_output is not None:
                destination = args.keep_output.resolve()
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(work_dir, destination)
    except (OSError, KeyError, ValueError, ValidationError) as exc:
        print("FAIL — fixed validation cases", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return 1

    for case_name, removed_labels in outcomes:
        rendered = ", ".join(removed_labels) if removed_labels else "none"
        print(f"PASS — {case_name}: removed {rendered}")
    print(f"PASS — all {len(outcomes)} fixed validation cases")
    print("Oracle and NEXCISION agreed on removed rows, retained rows, order,")
    print("state strings, dimensions, regional counts, and report checksums.")
    if args.keep_output is not None:
        print(f"Generated outputs copied to: {args.keep_output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

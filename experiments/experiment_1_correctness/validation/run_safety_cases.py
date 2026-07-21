#!/usr/bin/env python3
"""Run permanent NEXCISION safety validation cases."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class ValidationError(RuntimeError):
    """Raised when a safety case does not pass."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def compare_bytes(observed: Path, expected: Path, description: str) -> None:
    if observed.read_bytes() != expected.read_bytes():
        raise ValidationError(
            f"{description} differs from expected output:\n"
            f"  observed: {observed}\n  expected: {expected}"
        )


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_dimensions(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"\bdimensions\b[^;]*\bntax\s*=\s*(\d+)[^;]*\bnchar\s*=\s*(\d+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise ValidationError(f"Could not parse dimensions from {path}")
    return int(match.group(1)), int(match.group(2))


def matrix_row_count(path: Path) -> int:
    count = 0
    in_matrix = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not in_matrix:
            if stripped.lower() == "matrix":
                in_matrix = True
            continue
        if stripped == ";":
            return count
        if stripped and not stripped.startswith("["):
            count += 1
    raise ValidationError(f"Unterminated MATRIX block in {path}")


def validate_case(case_dir: Path, repo_root: Path, work_root: Path) -> None:
    input_nexus = case_dir / "input.nex"
    regions = case_dir / "regions.tsv"
    expected_error = (case_dir / "expected_default_stderr.txt").read_text(
        encoding="utf-8"
    )

    env = os.environ.copy()
    source_dir = str(repo_root / "src")
    env["PYTHONPATH"] = (
        source_dir
        if not env.get("PYTHONPATH")
        else source_dir + os.pathsep + env["PYTHONPATH"]
    )

    case_work = work_root / case_dir.name
    default_dir = case_work / "default"
    allowed_dir = case_work / "allow_empty"
    oracle_dir = case_work / "oracle"
    default_dir.mkdir(parents=True)
    allowed_dir.mkdir(parents=True)
    oracle_dir.mkdir(parents=True)

    # First independently confirm that every matrix row falls in the interval.
    oracle = repo_root / "validation" / "oracle" / "expected_rows.py"
    oracle_removed = oracle_dir / "removed.tsv"
    oracle_retained = oracle_dir / "retained.tsv"
    oracle_counts = oracle_dir / "counts.tsv"
    oracle_summary = oracle_dir / "summary.json"
    oracle_run = run(
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
    if oracle_run.returncode != 0:
        raise ValidationError(f"Oracle failed:\n{oracle_run.stderr}")
    compare_bytes(oracle_removed, case_dir / "expected_removed.tsv", "Oracle removed rows")
    compare_bytes(oracle_retained, case_dir / "expected_retained.tsv", "Oracle retained rows")
    compare_bytes(oracle_counts, case_dir / "expected_oracle_counts.tsv", "Oracle counts")
    compare_bytes(oracle_summary, case_dir / "expected_summary.json", "Oracle summary")

    # Default behaviour must fail safely and leave no outputs behind.
    default_output = default_dir / "filtered.nex"
    default_counts = default_dir / "counts.tsv"
    default_report = default_dir / "report.json"
    default_run = run(
        [
            sys.executable,
            "-m",
            "nexcision",
            str(input_nexus),
            str(regions),
            "--output",
            str(default_output),
            "--counts",
            str(default_counts),
            "--report",
            str(default_report),
        ],
        env=env,
    )
    if default_run.returncode != 2:
        raise ValidationError(
            f"Default run returned {default_run.returncode}; expected 2.\n"
            f"STDOUT:\n{default_run.stdout}\nSTDERR:\n{default_run.stderr}"
        )
    if default_run.stdout:
        raise ValidationError("Default safety failure unexpectedly wrote to stdout.")
    if default_run.stderr != expected_error:
        raise ValidationError(
            "Default safety error differed from expected text.\n"
            f"Observed: {default_run.stderr!r}\nExpected: {expected_error!r}"
        )
    unexpected = [path for path in (default_output, default_counts, default_report) if path.exists()]
    if unexpected:
        raise ValidationError(f"Default safety failure created outputs: {unexpected}")

    # Explicit override must produce a valid, intentionally empty matrix.
    allowed_output = allowed_dir / "filtered.nex"
    allowed_counts = allowed_dir / "counts.tsv"
    allowed_report = allowed_dir / "report.json"
    allowed_run = run(
        [
            sys.executable,
            "-m",
            "nexcision",
            str(input_nexus),
            str(regions),
            "--output",
            str(allowed_output),
            "--counts",
            str(allowed_counts),
            "--report",
            str(allowed_report),
            "--allow-empty",
        ],
        env=env,
    )
    if allowed_run.returncode != 0:
        raise ValidationError(
            f"--allow-empty run failed with {allowed_run.returncode}.\n"
            f"STDOUT:\n{allowed_run.stdout}\nSTDERR:\n{allowed_run.stderr}"
        )

    compare_bytes(
        allowed_output,
        case_dir / "expected_filtered_allow_empty.nex",
        "Allowed empty NEXUS",
    )
    compare_bytes(
        allowed_counts,
        case_dir / "expected_nexcision_counts.tsv",
        "Allowed empty counts",
    )

    if matrix_row_count(allowed_output) != 0:
        raise ValidationError("--allow-empty output still contains matrix rows.")
    ntax, nchar = parse_dimensions(allowed_output)
    if (ntax, nchar) != (4, 0):
        raise ValidationError(f"Allowed output dimensions are ntax={ntax}, nchar={nchar}; expected 4, 0.")

    counts = read_tsv(allowed_counts)
    if len(counts) != 1 or int(counts[0]["removed_rows"]) != 6:
        raise ValidationError(f"Allowed output counts are incorrect: {counts}")

    report = json.loads(allowed_report.read_text(encoding="utf-8"))
    results = report["results"]
    expected_results = {
        "regions_loaded": 1,
        "matrix_rows_read": 6,
        "rows_removed": 6,
        "rows_kept": 0,
        "unparsed_rows": 0,
        "dimension_updated": "nchar",
        "dimension_before": 6,
        "dimension_after": 0,
        "warnings": [],
    }
    for key, expected in expected_results.items():
        if results.get(key) != expected:
            raise ValidationError(
                f"Report field results.{key} is {results.get(key)!r}; expected {expected!r}."
            )
    if report["parameters"].get("allow_empty") is not True:
        raise ValidationError("Report does not record allow_empty=true.")
    if report["outputs"]["filtered_nexus"]["sha256"] != sha256(allowed_output):
        raise ValidationError("Filtered NEXUS checksum in report is incorrect.")
    if report["outputs"]["region_counts"]["sha256"] != sha256(allowed_counts):
        raise ValidationError("Counts checksum in report is incorrect.")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    cases_root = repo_root / "validation" / "safety_cases"
    case_dirs = sorted(path for path in cases_root.iterdir() if path.is_dir())
    try:
        with tempfile.TemporaryDirectory(prefix="nexcision-safety-cases-") as temp:
            work_root = Path(temp)
            for case_dir in case_dirs:
                validate_case(case_dir, repo_root, work_root)
    except (OSError, KeyError, ValueError, ValidationError) as exc:
        print("FAIL — safety validation cases", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return 1

    for case_dir in case_dirs:
        print(f"PASS — {case_dir.name}")
    print(f"PASS — all {len(case_dirs)} safety validation cases")
    print("Default empty-matrix protection and explicit --allow-empty behaviour agree with the specification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

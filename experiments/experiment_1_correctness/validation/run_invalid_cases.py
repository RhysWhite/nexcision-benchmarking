#!/usr/bin/env python3
"""Run permanent malformed-input and output-safety validation cases.

The cases exercise NEXCISION through its command-line interface. Every expected
failure must return exit code 2, write a clear error to stderr, leave stdout
empty, preserve all existing inputs, and create no unintended output files.
"""

from __future__ import annotations

import csv
import hashlib
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


VALID_NEXUS = """#NEXUS
Begin data;
Dimensions ntax=4 nchar=3;
Format datatype=standard symbols=\"01\" gap=- transpose;
Matrix
CP013831_160    0 1 0 1
CP013831_180    1 1 0 1
CP013831_200    0 0 1 1
;
End;
"""

VALID_REGIONS = """start\tend\tname
175\t185\ttest_region
"""


@dataclass(frozen=True)
class Case:
    case_id: str
    purpose: str
    expected_error: str
    prepare: Callable[[Path], tuple[Path, Path, Path, Path, Path, list[str]]]


class ValidationError(RuntimeError):
    """Raised when an invalid-input case behaves unexpectedly."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_valid_files(root: Path) -> tuple[Path, Path]:
    nexus = root / "input.nex"
    regions = root / "regions.tsv"
    nexus.write_text(VALID_NEXUS, encoding="utf-8")
    regions.write_text(VALID_REGIONS, encoding="utf-8")
    return nexus, regions


def standard_paths(root: Path) -> tuple[Path, Path, Path]:
    return root / "filtered.nex", root / "counts.tsv", root / "report.json"


def normal_case(
    *,
    nexus_text: str = VALID_NEXUS,
    regions_text: str = VALID_REGIONS,
    extra_args: list[str] | None = None,
) -> Callable[[Path], tuple[Path, Path, Path, Path, Path, list[str]]]:
    def prepare(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
        nexus = root / "input.nex"
        regions = root / "regions.tsv"
        nexus.write_text(nexus_text, encoding="utf-8")
        regions.write_text(regions_text, encoding="utf-8")
        output, counts, report = standard_paths(root)
        return nexus, regions, output, counts, report, list(extra_args or [])

    return prepare


def invalid_utf8_nexus(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus = root / "input.nex"
    regions = root / "regions.tsv"
    nexus.write_bytes(b"#NEXUS\n\xff\xfe\n")
    regions.write_text(VALID_REGIONS, encoding="utf-8")
    output, counts, report = standard_paths(root)
    return nexus, regions, output, counts, report, []


def invalid_utf8_regions(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus = root / "input.nex"
    regions = root / "regions.tsv"
    nexus.write_text(VALID_NEXUS, encoding="utf-8")
    regions.write_bytes(b"start\tend\n175\t185\n\xff\xfe")
    output, counts, report = standard_paths(root)
    return nexus, regions, output, counts, report, []


def missing_nexus(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus = root / "missing.nex"
    regions = root / "regions.tsv"
    regions.write_text(VALID_REGIONS, encoding="utf-8")
    output, counts, report = standard_paths(root)
    return nexus, regions, output, counts, report, []


def missing_regions(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus = root / "input.nex"
    regions = root / "missing.tsv"
    nexus.write_text(VALID_NEXUS, encoding="utf-8")
    output, counts, report = standard_paths(root)
    return nexus, regions, output, counts, report, []


def output_equals_input(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus, regions = write_valid_files(root)
    _output, counts, report = standard_paths(root)
    return nexus, regions, nexus, counts, report, []


def duplicate_outputs(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus, regions = write_valid_files(root)
    shared = root / "same.tsv"
    report = root / "report.json"
    return nexus, regions, shared, shared, report, []


def existing_output(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus, regions = write_valid_files(root)
    output, counts, report = standard_paths(root)
    output.write_text("DO NOT REPLACE\n", encoding="utf-8")
    return nexus, regions, output, counts, report, []


def output_is_directory(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus, regions = write_valid_files(root)
    output = root / "filtered.nex"
    output.mkdir()
    counts = root / "counts.tsv"
    report = root / "report.json"
    return nexus, regions, output, counts, report, ["--force"]


def output_parent_is_file(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus, regions = write_valid_files(root)
    blocker = root / "not_a_directory"
    blocker.write_text("blocker\n", encoding="utf-8")
    output = root / "filtered.nex"
    counts = blocker / "counts.tsv"
    report = root / "report.json"
    return nexus, regions, output, counts, report, []


def nested_outputs(root: Path) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    nexus, regions = write_valid_files(root)
    output = root / "filtered.nex"
    counts = output / "counts.tsv"
    report = root / "report.json"
    return nexus, regions, output, counts, report, []


def cases() -> list[Case]:
    missing_matrix = VALID_NEXUS.replace("Matrix\n", "")
    multiple_matrix = VALID_NEXUS + "\nBegin data;\nMatrix\nCP013831_220 0 0 0 0\n;\nEnd;\n"
    unterminated = VALID_NEXUS.replace("\n;\nEnd;\n", "\nEnd;\n")
    end_before_terminator = VALID_NEXUS.replace("\n;\nEnd;\n", "\nEnd;\n;\n")
    no_rows = VALID_NEXUS.replace(
        "CP013831_160    0 1 0 1\nCP013831_180    1 1 0 1\nCP013831_200    0 0 1 1\n",
        "[comment only]\n\n",
    )
    unparseable = VALID_NEXUS.replace("CP013831_180", "not_a_coordinate")
    interleaved = VALID_NEXUS.replace(
        "CP013831_180    1 1 0 1\n",
        "CP013831_180    1 1\n1 0 1\n",
    )

    return [
        Case("invalid_001_missing_matrix", "missing MATRIX command", "No standalone MATRIX line", normal_case(nexus_text=missing_matrix)),
        Case("invalid_002_multiple_matrices", "multiple MATRIX blocks", "More than one MATRIX block", normal_case(nexus_text=multiple_matrix)),
        Case("invalid_003_unterminated_matrix", "MATRIX lacks terminating semicolon", "MATRIX block is not terminated", normal_case(nexus_text=unterminated)),
        Case("invalid_004_end_before_terminator", "enclosing block ends before MATRIX", "MATRIX block is not terminated before the enclosing block ends", normal_case(nexus_text=end_before_terminator)),
        Case("invalid_005_no_coordinate_rows", "MATRIX contains no coordinate-labelled rows", "No coordinate-labelled rows were parsed", normal_case(nexus_text=no_rows)),
        Case("invalid_006_unparseable_row", "matrix row does not match coordinate pattern", "does not match the position pattern", normal_case(nexus_text=unparseable)),
        Case("invalid_007_interleaved_matrix", "unsupported interleaved continuation row", "does not match the position pattern", normal_case(nexus_text=interleaved)),
        Case("invalid_008_empty_regions", "empty regions file", "No valid regions were found", normal_case(regions_text="")),
        Case("invalid_009_header_only_regions", "regions file contains only header", "No valid regions were found", normal_case(regions_text="start\tend\tname\n")),
        Case("invalid_010_missing_end", "region row has one field", "must contain start and end", normal_case(regions_text="175\n")),
        Case("invalid_011_noninteger_region", "region coordinate is non-integer", "has non-integer coordinates", normal_case(regions_text="start\tend\nabc\t185\n")),
        Case("invalid_012_zero_region", "region coordinate is zero", "contains a coordinate below 1", normal_case(regions_text="0\t185\n")),
        Case("invalid_013_negative_region", "region coordinate is negative", "contains a coordinate below 1", normal_case(regions_text="-5\t185\n")),
        Case("invalid_014_invalid_regex", "syntactically invalid coordinate regex", "Invalid position regular expression", normal_case(extra_args=["--position-regex", "("])),
        Case("invalid_015_regex_no_group", "coordinate regex lacks capture group", "must contain exactly one capture group", normal_case(extra_args=["--position-regex", r"_\d+$"])),
        Case("invalid_016_regex_two_groups", "coordinate regex has two capture groups", "must contain exactly one capture group", normal_case(extra_args=["--position-regex", r"_(\d+)(\d+)$"])),
        Case("invalid_017_missing_nexus", "NEXUS file does not exist", "Cannot open NEXUS file", missing_nexus),
        Case("invalid_018_missing_regions", "regions file does not exist", "Cannot open regions file", missing_regions),
        Case("invalid_019_invalid_utf8_nexus", "NEXUS file is not valid UTF-8", "Cannot open NEXUS file", invalid_utf8_nexus),
        Case("invalid_020_invalid_utf8_regions", "regions file is not valid UTF-8", "Cannot decode regions file", invalid_utf8_regions),
        Case("invalid_021_output_equals_input", "output would overwrite input", "Output paths must not overwrite an input file", output_equals_input),
        Case("invalid_022_duplicate_outputs", "two output paths are identical", "Every output path must be different", duplicate_outputs),
        Case("invalid_023_existing_output", "existing output without --force", "Output file already exists", existing_output),
        Case("invalid_024_output_is_directory", "output path is a directory", "Output path is a directory", output_is_directory),
        Case("invalid_025_parent_is_file", "output parent path is a file", "Output parent path is not a directory", output_parent_is_file),
        Case("invalid_026_nested_outputs", "one output path is nested beneath another", "Output paths must not be nested", nested_outputs),
    ]


def snapshots(root: Path) -> dict[Path, str]:
    result: dict[Path, str] = {}
    for path in root.rglob("*"):
        if path.is_file():
            result[path.relative_to(root)] = sha256(path)
    return result


def run_case(case: Case, root: Path, repo_root: Path) -> dict[str, str]:
    case_root = root / case.case_id
    case_root.mkdir()
    nexus, regions, output, counts, report, extra_args = case.prepare(case_root)
    before = snapshots(case_root)

    env = os.environ.copy()
    source_dir = str(repo_root / "src")
    env["PYTHONPATH"] = (
        source_dir
        if not env.get("PYTHONPATH")
        else source_dir + os.pathsep + env["PYTHONPATH"]
    )

    command = [
        sys.executable,
        "-m",
        "nexcision",
        str(nexus),
        str(regions),
        "--output",
        str(output),
        "--counts",
        str(counts),
        "--report",
        str(report),
        *extra_args,
    ]
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    if completed.returncode != 2:
        raise ValidationError(
            f"{case.case_id} returned {completed.returncode}; expected 2.\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    if completed.stdout:
        raise ValidationError(
            f"{case.case_id} unexpectedly wrote to stdout: {completed.stdout!r}"
        )
    if case.expected_error not in completed.stderr:
        raise ValidationError(
            f"{case.case_id} stderr did not contain {case.expected_error!r}.\n"
            f"Observed: {completed.stderr!r}"
        )
    if not completed.stderr.startswith("ERROR: "):
        raise ValidationError(
            f"{case.case_id} did not use the standard ERROR prefix: "
            f"{completed.stderr!r}"
        )

    after = snapshots(case_root)
    for relative, checksum in before.items():
        if after.get(relative) != checksum:
            raise ValidationError(
                f"{case.case_id} modified pre-existing file {relative}."
            )

    permitted = set(before)
    unexpected = sorted(set(after) - permitted)
    if unexpected:
        raise ValidationError(
            f"{case.case_id} created unexpected files: {unexpected}"
        )

    leftovers = [
        path.relative_to(case_root)
        for path in case_root.rglob("*")
        if path.is_file() and path.suffix in {".tmp", ".bak"}
    ]
    if leftovers:
        raise ValidationError(
            f"{case.case_id} left temporary files behind: {leftovers}"
        )

    return {
        "case_id": case.case_id,
        "purpose": case.purpose,
        "expected_exit_code": "2",
        "observed_exit_code": str(completed.returncode),
        "error_check": "PASS",
        "stdout_empty": "PASS",
        "inputs_preserved": "PASS",
        "no_unintended_outputs": "PASS",
        "temporary_files_removed": "PASS",
        "overall": "PASS",
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    output_results: Path | None = None
    if len(sys.argv) == 3 and sys.argv[1] == "--results":
        output_results = Path(sys.argv[2])
    elif len(sys.argv) != 1:
        print("Usage: run_invalid_cases.py [--results PATH]", file=sys.stderr)
        return 2

    all_cases = cases()
    try:
        with tempfile.TemporaryDirectory(prefix="nexcision-invalid-cases-") as temp:
            root = Path(temp)
            results = [run_case(case, root, repo_root) for case in all_cases]
    except (OSError, ValidationError) as exc:
        print("FAIL — malformed-input and output-safety validation", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return 1

    if output_results is not None:
        output_results.parent.mkdir(parents=True, exist_ok=True)
        with output_results.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(results[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(results)

    for result in results:
        print(f"PASS — {result['case_id']}")
    print(f"PASS — all {len(results)} malformed-input and output-safety cases")
    print("Every expected failure returned exit code 2 without modifying inputs or creating unintended outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

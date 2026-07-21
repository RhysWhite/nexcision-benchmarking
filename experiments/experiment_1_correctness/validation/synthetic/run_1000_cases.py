#!/usr/bin/env python3
"""Validate 1,000 deterministic synthetic NEXCISION correctness cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
    if completed.returncode != 0:
        raise ValidationError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_matrix(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    in_matrix = False
    blocks = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not in_matrix:
            if stripped.lower() == "matrix":
                in_matrix = True
                blocks += 1
            continue
        if stripped == ";":
            in_matrix = False
            continue
        if not stripped or stripped.startswith("["):
            continue
        fields = stripped.split(maxsplit=1)
        if len(fields) != 2:
            raise ValidationError(f"Malformed matrix row in {path}: {stripped!r}")
        rows.append((fields[0], fields[1]))
    if blocks != 1 or in_matrix:
        raise ValidationError(f"Could not parse one complete MATRIX block in {path}")
    return rows


def dimensions(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"\bdimensions\b[^;]*\bntax\s*=\s*(\d+)[^;]*\bnchar\s*=\s*(\d+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise ValidationError(f"Could not parse dimensions in {path}")
    return int(match.group(1)), int(match.group(2))


def removed_rows(original: list[tuple[str, str]], filtered: list[tuple[str, str]]) -> list[tuple[str, str]]:
    retained = Counter(filtered)
    result: list[tuple[str, str]] = []
    for row in original:
        if retained[row]:
            retained[row] -= 1
        else:
            result.append(row)
    return result


def compare_bytes(observed: Path, expected: Path, label: str, case_id: str) -> None:
    if observed.read_bytes() != expected.read_bytes():
        raise ValidationError(f"{label} differs in {case_id}")


def tool_command(
    tool_python: Path,
    input_nexus: Path,
    regions: Path,
    output: Path,
    counts: Path,
    report: Path,
    force: bool,
) -> list[str]:
    command = [
        str(tool_python), "-m", "nexcision", str(input_nexus), str(regions),
        "--output", str(output), "--counts", str(counts), "--report", str(report),
    ]
    if force:
        command.append("--force")
    return command


def validate_case(
    case_dir: Path,
    repo_root: Path,
    oracle: Path,
    work_root: Path,
    manifest_by_id: dict[str, dict[str, str]],
    tool_python: Path,
    use_source: bool,
) -> dict[str, object]:
    case_id = case_dir.name
    input_nexus = case_dir / "input.nex"
    regions = case_dir / "regions.tsv"
    expected_summary = json.loads((case_dir / "expected_summary.json").read_text(encoding="utf-8"))

    case_work = work_root / case_id
    oracle_work = case_work / "oracle"
    tool_work = case_work / "nexcision"
    oracle_work.mkdir(parents=True)
    tool_work.mkdir(parents=True)

    oracle_removed = oracle_work / "removed.tsv"
    oracle_retained = oracle_work / "retained.tsv"
    oracle_counts = oracle_work / "counts.tsv"
    oracle_summary = oracle_work / "summary.json"
    run([
        sys.executable, str(oracle), str(input_nexus), str(regions),
        "--removed", str(oracle_removed),
        "--retained", str(oracle_retained),
        "--counts", str(oracle_counts),
        "--summary", str(oracle_summary),
    ])

    compare_bytes(oracle_removed, case_dir / "expected_removed.tsv", "Oracle removed rows", case_id)
    compare_bytes(oracle_retained, case_dir / "expected_retained.tsv", "Oracle retained rows", case_id)
    compare_bytes(oracle_counts, case_dir / "expected_oracle_counts.tsv", "Oracle counts", case_id)
    compare_bytes(oracle_summary, case_dir / "expected_summary.json", "Oracle summary", case_id)

    output = tool_work / "filtered.nex"
    counts = tool_work / "counts.tsv"
    report = tool_work / "report.json"
    env = os.environ.copy()
    if use_source:
        source = str(repo_root / "src")
        env["PYTHONPATH"] = source if not env.get("PYTHONPATH") else source + os.pathsep + env["PYTHONPATH"]

    start = time.perf_counter()
    run(tool_command(tool_python, input_nexus, regions, output, counts, report, force=False), env=env)
    elapsed = time.perf_counter() - start

    compare_bytes(output, case_dir / "expected_filtered.nex", "Filtered NEXUS", case_id)
    compare_bytes(counts, case_dir / "expected_nexcision_counts.tsv", "NEXCISION counts", case_id)

    original = parse_matrix(input_nexus)
    filtered = parse_matrix(output)
    removed = removed_rows(original, filtered)
    expected_removed_labels = [row["row_label"] for row in read_tsv(oracle_removed)]
    expected_retained_labels = [row["row_label"] for row in read_tsv(oracle_retained)]
    if [row[0] for row in removed] != expected_removed_labels:
        raise ValidationError(f"Removed-row disagreement in {case_id}")
    if [row[0] for row in filtered] != expected_retained_labels:
        raise ValidationError(f"Retained-row/order disagreement in {case_id}")

    retained_counter = Counter(filtered)
    exact_expected: list[tuple[str, str]] = []
    for row in original:
        if retained_counter[row]:
            retained_counter[row] -= 1
            exact_expected.append(row)
    if filtered != exact_expected:
        raise ValidationError(f"Retained state text changed in {case_id}")

    ntax_before, nchar_before = dimensions(input_nexus)
    ntax_after, nchar_after = dimensions(output)
    if ntax_before != ntax_after:
        raise ValidationError(f"ntax changed in {case_id}")
    if nchar_after != expected_summary["expected_rows_retained"]:
        raise ValidationError(f"nchar is incorrect in {case_id}")

    oracle_count_values = [int(row["expected_removed_rows"]) for row in read_tsv(oracle_counts)]
    tool_count_values = [int(row["removed_rows"]) for row in read_tsv(counts)]
    if oracle_count_values != tool_count_values:
        raise ValidationError(f"Per-region count disagreement in {case_id}")

    report_data = json.loads(report.read_text(encoding="utf-8"))
    results = report_data["results"]
    required_report = {
        "regions_loaded": expected_summary["regions_loaded"],
        "matrix_rows_read": expected_summary["matrix_rows_read"],
        "rows_removed": expected_summary["expected_rows_removed"],
        "rows_kept": expected_summary["expected_rows_retained"],
        "unparsed_rows": 0,
        "dimension_updated": "nchar",
        "dimension_before": nchar_before,
        "dimension_after": nchar_after,
        "warnings": [],
    }
    for key, expected in required_report.items():
        if results.get(key) != expected:
            raise ValidationError(f"Incorrect report field {key} in {case_id}")
    if report_data["outputs"]["filtered_nexus"]["sha256"] != sha256(output):
        raise ValidationError(f"Output checksum mismatch in {case_id}")
    if report_data["outputs"]["region_counts"]["sha256"] != sha256(counts):
        raise ValidationError(f"Counts checksum mismatch in {case_id}")

    first_hashes = (sha256(output), sha256(counts), sha256(report))
    run(tool_command(tool_python, input_nexus, regions, output, counts, report, force=True), env=env)
    second_hashes = (sha256(output), sha256(counts), sha256(report))
    if first_hashes != second_hashes:
        raise ValidationError(f"Repeat-run output was not deterministic in {case_id}")

    manifest_row = manifest_by_id[case_id]
    return {
        "case_id": case_id,
        "family": manifest_row["family"],
        "seed": manifest_row["seed"],
        "ntax": ntax_before,
        "nchar_before": nchar_before,
        "interval_count": expected_summary["regions_loaded"],
        "row_order": manifest_row["row_order"],
        "separator": manifest_row["separator"],
        "rows_removed": expected_summary["expected_rows_removed"],
        "rows_retained": expected_summary["expected_rows_retained"],
        "removal_fraction": manifest_row["removal_fraction"],
        "input_bytes": input_nexus.stat().st_size,
        "runtime_seconds": f"{elapsed:.6f}",
        "oracle_agreement": "PASS",
        "retained_rows_exact": "PASS",
        "dimensions": "PASS",
        "region_counts": "PASS",
        "report_checksums": "PASS",
        "repeat_determinism": "PASS",
        "overall": "PASS",
    }


def write_results(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run 1,000 synthetic NEXCISION correctness cases.")
    parser.add_argument("--results", type=Path, help="TSV path for machine-readable results.")
    parser.add_argument("--summary", type=Path, help="JSON path for aggregate results.")
    parser.add_argument(
        "--tool-python",
        type=Path,
        default=Path(sys.executable),
        help="Python executable containing the installed NEXCISION package.",
    )
    parser.add_argument(
        "--use-source",
        action="store_true",
        help="Add the repository src directory to PYTHONPATH for tool execution.",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="First 1-based case index to run (default: 1).",
    )
    parser.add_argument(
        "--end-index",
        type=int,
        default=1000,
        help="Last 1-based case index to run, inclusive (default: 1000).",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    synthetic_root = Path(__file__).resolve().parent
    cases_root = synthetic_root / "cases_1000"
    manifest_path = synthetic_root / "case_1000_manifest.tsv"
    oracle = repo_root / "validation" / "oracle" / "expected_rows.py"
    case_dirs = sorted(path for path in cases_root.iterdir() if path.is_dir())
    if len(case_dirs) != 1000:
        print(f"FAIL — expected 1,000 synthetic cases, found {len(case_dirs)}", file=sys.stderr)
        return 1
    if not (1 <= args.start_index <= args.end_index <= 1000):
        print("FAIL — require 1 <= start-index <= end-index <= 1000", file=sys.stderr)
        return 1
    case_dirs = case_dirs[args.start_index - 1:args.end_index]
    selected_count = len(case_dirs)

    manifest_rows = read_tsv(manifest_path)
    manifest_by_id = {row["case_id"]: row for row in manifest_rows}
    if len(manifest_by_id) != 1000:
        print("FAIL — manifest does not contain 1,000 unique cases", file=sys.stderr)
        return 1

    tool_python = args.tool_python.absolute()
    if not tool_python.exists():
        print(f"FAIL — tool Python does not exist: {tool_python}", file=sys.stderr)
        return 1

    try:
        with tempfile.TemporaryDirectory(prefix="nexcision-synthetic-1000-") as temp:
            rows: list[dict[str, object]] = []
            for index, case_dir in enumerate(case_dirs, start=1):
                rows.append(
                    validate_case(
                        case_dir,
                        repo_root,
                        oracle,
                        Path(temp),
                        manifest_by_id,
                        tool_python,
                        args.use_source,
                    )
                )
                if index % 50 == 0 or index == selected_count:
                    print(f"Validated {index}/{selected_count} selected cases...", flush=True)
    except (OSError, KeyError, ValueError, ValidationError) as exc:
        print("FAIL — 1,000-case synthetic validation", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return 1

    if args.results is not None:
        write_results(args.results, rows)

    runtimes = [float(row["runtime_seconds"]) for row in rows]
    aggregate = {
        "cases": len(rows),
        "cases_passed": sum(row["overall"] == "PASS" for row in rows),
        "families": sorted({str(row["family"]) for row in rows}),
        "total_site_rows": sum(int(row["nchar_before"]) for row in rows),
        "total_rows_removed": sum(int(row["rows_removed"]) for row in rows),
        "total_rows_retained": sum(int(row["rows_retained"]) for row in rows),
        "total_input_bytes": sum(int(row["input_bytes"]) for row in rows),
        "minimum_taxa": min(int(row["ntax"]) for row in rows),
        "maximum_taxa": max(int(row["ntax"]) for row in rows),
        "minimum_sites": min(int(row["nchar_before"]) for row in rows),
        "maximum_sites": max(int(row["nchar_before"]) for row in rows),
        "minimum_intervals": min(int(row["interval_count"]) for row in rows),
        "maximum_intervals": max(int(row["interval_count"]) for row in rows),
        "minimum_removal_fraction": min(float(row["removal_fraction"]) for row in rows),
        "maximum_removal_fraction": max(float(row["removal_fraction"]) for row in rows),
        "median_runtime_seconds": sorted(runtimes)[len(runtimes) // 2],
        "maximum_runtime_seconds": max(runtimes),
        "all_oracle_agreement": all(row["oracle_agreement"] == "PASS" for row in rows),
        "all_outputs_exact": all(row["retained_rows_exact"] == "PASS" for row in rows),
        "all_dimensions_correct": all(row["dimensions"] == "PASS" for row in rows),
        "all_region_counts_correct": all(row["region_counts"] == "PASS" for row in rows),
        "all_report_checksums_correct": all(row["report_checksums"] == "PASS" for row in rows),
        "all_repeat_runs_deterministic": all(row["repeat_determinism"] == "PASS" for row in rows),
        "tool_python": str(tool_python),
        "tool_mode": "source" if args.use_source else "installed_package",
    }
    if args.summary is not None:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"PASS — all {len(rows)} selected synthetic correctness cases")
    print(
        "Oracle and NEXCISION agreed exactly on row membership, order, states, "
        "dimensions, per-region counts, checksums, and repeat-run determinism."
    )
    if args.results is not None:
        print(f"Results written to: {args.results.resolve()}")
    if args.summary is not None:
        print(f"Summary written to: {args.summary.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

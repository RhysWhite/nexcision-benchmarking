#!/usr/bin/env python3
"""Validate the ten deterministic synthetic NEXCISION pilot cases."""

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
from collections import Counter
from pathlib import Path


class PilotValidationError(RuntimeError):
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
        raise PilotValidationError(
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
            raise PilotValidationError(f"Malformed matrix row in {path}: {stripped!r}")
        rows.append((fields[0], fields[1]))
    if blocks != 1 or in_matrix:
        raise PilotValidationError(f"Could not parse one complete MATRIX block in {path}")
    return rows


def dimensions(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"\bdimensions\b[^;]*\bntax\s*=\s*(\d+)[^;]*\bnchar\s*=\s*(\d+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise PilotValidationError(f"Could not parse dimensions in {path}")
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


def compare_bytes(observed: Path, expected: Path, label: str) -> None:
    if observed.read_bytes() != expected.read_bytes():
        raise PilotValidationError(f"{label} differs for {observed.parent.parent.name}")


def validate_case(case_dir: Path, repo_root: Path, oracle: Path, work_root: Path) -> dict[str, object]:
    input_nexus = case_dir / "input.nex"
    regions = case_dir / "regions.tsv"
    expected_summary = json.loads((case_dir / "expected_summary.json").read_text(encoding="utf-8"))

    case_work = work_root / case_dir.name
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

    compare_bytes(oracle_removed, case_dir / "expected_removed.tsv", "Oracle removed rows")
    compare_bytes(oracle_retained, case_dir / "expected_retained.tsv", "Oracle retained rows")
    compare_bytes(oracle_counts, case_dir / "expected_oracle_counts.tsv", "Oracle counts")
    compare_bytes(oracle_summary, case_dir / "expected_summary.json", "Oracle summary")

    output = tool_work / "filtered.nex"
    counts = tool_work / "counts.tsv"
    report = tool_work / "report.json"
    env = os.environ.copy()
    source = str(repo_root / "src")
    env["PYTHONPATH"] = source if not env.get("PYTHONPATH") else source + os.pathsep + env["PYTHONPATH"]
    run([
        sys.executable, "-m", "nexcision", str(input_nexus), str(regions),
        "--output", str(output), "--counts", str(counts), "--report", str(report),
    ], env=env)

    compare_bytes(output, case_dir / "expected_filtered.nex", "Filtered NEXUS")
    compare_bytes(counts, case_dir / "expected_nexcision_counts.tsv", "NEXCISION counts")

    original = parse_matrix(input_nexus)
    filtered = parse_matrix(output)
    removed = removed_rows(original, filtered)
    expected_removed_labels = [row["row_label"] for row in read_tsv(oracle_removed)]
    expected_retained_labels = [row["row_label"] for row in read_tsv(oracle_retained)]
    if [row[0] for row in removed] != expected_removed_labels:
        raise PilotValidationError(f"Removed-row disagreement in {case_dir.name}")
    if [row[0] for row in filtered] != expected_retained_labels:
        raise PilotValidationError(f"Retained-row/order disagreement in {case_dir.name}")

    retained_counter = Counter(filtered)
    exact_expected: list[tuple[str, str]] = []
    for row in original:
        if retained_counter[row]:
            retained_counter[row] -= 1
            exact_expected.append(row)
    if filtered != exact_expected:
        raise PilotValidationError(f"Retained state text changed in {case_dir.name}")

    ntax_before, nchar_before = dimensions(input_nexus)
    ntax_after, nchar_after = dimensions(output)
    if ntax_before != ntax_after:
        raise PilotValidationError(f"ntax changed in {case_dir.name}")
    if nchar_after != expected_summary["expected_rows_retained"]:
        raise PilotValidationError(f"nchar is incorrect in {case_dir.name}")

    oracle_count_values = [int(row["expected_removed_rows"]) for row in read_tsv(oracle_counts)]
    tool_count_values = [int(row["removed_rows"]) for row in read_tsv(counts)]
    if oracle_count_values != tool_count_values:
        raise PilotValidationError(f"Per-region count disagreement in {case_dir.name}")

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
            raise PilotValidationError(f"Incorrect report field {key} in {case_dir.name}")
    if report_data["outputs"]["filtered_nexus"]["sha256"] != sha256(output):
        raise PilotValidationError(f"Output checksum mismatch in {case_dir.name}")
    if report_data["outputs"]["region_counts"]["sha256"] != sha256(counts):
        raise PilotValidationError(f"Counts checksum mismatch in {case_dir.name}")

    manifest_row = next(row for row in read_tsv(case_dir.parent.parent / "pilot_case_manifest.tsv") if row["case_id"] == case_dir.name)
    return {
        "case_id": case_dir.name,
        "ntax": ntax_before,
        "nchar_before": nchar_before,
        "interval_count": expected_summary["regions_loaded"],
        "row_order": manifest_row["row_order"],
        "interval_geometry": manifest_row["interval_geometry"],
        "rows_removed": expected_summary["expected_rows_removed"],
        "rows_retained": expected_summary["expected_rows_retained"],
        "removal_fraction": manifest_row["removal_fraction"],
        "oracle_agreement": "PASS",
        "retained_rows_exact": "PASS",
        "dimensions": "PASS",
        "region_counts": "PASS",
        "report_checksums": "PASS",
        "overall": "PASS",
    }


def write_results(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ten synthetic NEXCISION pilot cases.")
    parser.add_argument("--results", type=Path, help="Optional TSV path for the machine-readable results.")
    parser.add_argument("--summary", type=Path, help="Optional JSON path for an aggregate summary.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    synthetic_root = Path(__file__).resolve().parent
    cases_root = synthetic_root / "pilot_cases"
    oracle = repo_root / "validation" / "oracle" / "expected_rows.py"
    case_dirs = sorted(path for path in cases_root.iterdir() if path.is_dir())
    if len(case_dirs) != 10:
        print(f"FAIL — expected 10 synthetic pilot cases, found {len(case_dirs)}", file=sys.stderr)
        return 1

    try:
        with tempfile.TemporaryDirectory(prefix="nexcision-synthetic-pilot-") as temp:
            rows = [validate_case(case_dir, repo_root, oracle, Path(temp)) for case_dir in case_dirs]
    except (OSError, KeyError, ValueError, PilotValidationError) as exc:
        print("FAIL — synthetic pilot validation", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return 1

    if args.results is not None:
        write_results(args.results, rows)
    if args.summary is not None:
        aggregate = {
            "cases": len(rows),
            "cases_passed": sum(row["overall"] == "PASS" for row in rows),
            "total_site_rows": sum(int(row["nchar_before"]) for row in rows),
            "total_rows_removed": sum(int(row["rows_removed"]) for row in rows),
            "total_rows_retained": sum(int(row["rows_retained"]) for row in rows),
            "minimum_taxa": min(int(row["ntax"]) for row in rows),
            "maximum_taxa": max(int(row["ntax"]) for row in rows),
            "minimum_intervals": min(int(row["interval_count"]) for row in rows),
            "maximum_intervals": max(int(row["interval_count"]) for row in rows),
            "all_oracle_agreement": all(row["oracle_agreement"] == "PASS" for row in rows),
            "all_outputs_exact": all(row["retained_rows_exact"] == "PASS" for row in rows),
            "all_dimensions_correct": all(row["dimensions"] == "PASS" for row in rows),
            "all_region_counts_correct": all(row["region_counts"] == "PASS" for row in rows),
            "all_report_checksums_correct": all(row["report_checksums"] == "PASS" for row in rows),
        }
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(
            json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    for row in rows:
        print(
            f"PASS — {row['case_id']}: "
            f"{row['rows_removed']}/{row['nchar_before']} rows removed"
        )
    print("PASS — all 10 synthetic pilot cases")
    print("Oracle and NEXCISION agreed exactly on row membership, order, states,")
    print("dimensions, per-region counts, and report checksums.")
    if args.results is not None:
        print(f"Results written to: {args.results.resolve()}")
    if args.summary is not None:
        print(f"Summary written to: {args.summary.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

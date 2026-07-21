#!/usr/bin/env python3
"""Run the full 1,000-case NEXCISION correctness corpus in one process.

The script is intended to be executed with the clean virtual environment that
contains the built NEXCISION wheel. Expected membership is calculated by the
independent naive oracle under ``validation/oracle``. NEXCISION itself is
loaded from the installed wheel, not from the repository source tree.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import re
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType

from nexcision import __version__
from nexcision.core import filter_nexus_file


class ValidationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_oracle(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("nexcision_validation_oracle", path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"Could not load oracle: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_matrix(path: Path) -> list[tuple[str, str]]:
    """Return ordered (label, exact state text) pairs from one MATRIX block."""
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[tuple[str, str]] = []
    in_matrix = False
    matrix_blocks = 0
    for raw in lines:
        stripped = raw.strip()
        if not in_matrix:
            if stripped.lower() == "matrix":
                in_matrix = True
                matrix_blocks += 1
            continue
        before, sep, _after = raw.partition(";")
        content = before.strip() if sep else stripped
        if content and not content.startswith("["):
            parts = content.split(maxsplit=1)
            if len(parts) != 2:
                raise ValidationError(f"Malformed matrix row in {path}: {content!r}")
            rows.append((parts[0].strip("'\""), parts[1]))
        if sep:
            in_matrix = False
    if in_matrix or matrix_blocks != 1:
        raise ValidationError(f"Could not parse exactly one terminated MATRIX in {path}")
    return rows


def dimensions(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"\bdimensions\b(?:(?!;).)*?\bntax\s*=\s*(\d+)"
        r"(?:(?!;).)*?\bnchar\s*=\s*(\d+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise ValidationError(f"Could not parse dimensions in {path}")
    return int(match.group(1)), int(match.group(2))


def removed_rows(
    original: list[tuple[str, str]], filtered: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    retained = Counter(filtered)
    removed: list[tuple[str, str]] = []
    for row in original:
        if retained[row]:
            retained[row] -= 1
        else:
            removed.append(row)
    return removed


def compare_bytes(observed: Path, expected: Path, label: str, case_id: str) -> None:
    if observed.read_bytes() != expected.read_bytes():
        raise ValidationError(f"{label} differs in {case_id}")


def validate_case(
    case_dir: Path,
    work_root: Path,
    manifest_row: dict[str, str],
    oracle: ModuleType,
) -> dict[str, object]:
    case_id = case_dir.name
    input_nexus = case_dir / "input.nex"
    regions_path = case_dir / "regions.tsv"
    expected_summary = json.loads(
        (case_dir / "expected_summary.json").read_text(encoding="utf-8")
    )

    # Independent oracle: naive membership against every original region.
    oracle_regions = oracle.load_regions(regions_path)
    oracle_rows = oracle.load_matrix_rows(input_nexus)
    oracle_removed = [row for row in oracle_rows if oracle.should_remove(row, oracle_regions)]
    oracle_retained = [row for row in oracle_rows if not oracle.should_remove(row, oracle_regions)]
    expected_removed_labels = [row["row_label"] for row in read_tsv(case_dir / "expected_removed.tsv")]
    expected_retained_labels = [row["row_label"] for row in read_tsv(case_dir / "expected_retained.tsv")]
    if [row.label for row in oracle_removed] != expected_removed_labels:
        raise ValidationError(f"Oracle removed-row disagreement in {case_id}")
    if [row.label for row in oracle_retained] != expected_retained_labels:
        raise ValidationError(f"Oracle retained-row disagreement in {case_id}")

    expected_oracle_counts = [
        int(row["expected_removed_rows"])
        for row in read_tsv(case_dir / "expected_oracle_counts.tsv")
    ]
    oracle_counts = [
        sum(oracle.row_matches_region(row, region) for row in oracle_removed)
        for region in oracle_regions
    ]
    if oracle_counts != expected_oracle_counts:
        raise ValidationError(f"Oracle count disagreement in {case_id}")

    case_work = work_root / case_id
    case_work.mkdir(parents=True)
    output = case_work / "filtered.nex"
    counts = case_work / "counts.tsv"
    report = case_work / "report.json"

    start = time.perf_counter()
    result = filter_nexus_file(
        input_nexus,
        regions_path,
        output,
        counts,
        report_path=report,
    )
    elapsed = time.perf_counter() - start

    compare_bytes(output, case_dir / "expected_filtered.nex", "Filtered NEXUS", case_id)
    compare_bytes(counts, case_dir / "expected_nexcision_counts.tsv", "Counts", case_id)

    original = parse_matrix(input_nexus)
    filtered = parse_matrix(output)
    removed = removed_rows(original, filtered)
    if [row[0] for row in removed] != expected_removed_labels:
        raise ValidationError(f"NEXCISION removed-row disagreement in {case_id}")
    if [row[0] for row in filtered] != expected_retained_labels:
        raise ValidationError(f"Retained-row/order disagreement in {case_id}")

    # Exact retained row and state-text preservation.
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

    tool_counts = [int(row["removed_rows"]) for row in read_tsv(counts)]
    if tool_counts != oracle_counts:
        raise ValidationError(f"Per-region count disagreement in {case_id}")

    if result.rows_removed != expected_summary["expected_rows_removed"]:
        raise ValidationError(f"FilterResult rows_removed incorrect in {case_id}")
    if result.rows_kept != expected_summary["expected_rows_retained"]:
        raise ValidationError(f"FilterResult rows_kept incorrect in {case_id}")

    report_data = json.loads(report.read_text(encoding="utf-8"))
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
        if report_data["results"].get(key) != expected:
            raise ValidationError(f"Incorrect report field {key} in {case_id}")
    if report_data["outputs"]["filtered_nexus"]["sha256"] != sha256(output):
        raise ValidationError(f"Output checksum mismatch in {case_id}")
    if report_data["outputs"]["region_counts"]["sha256"] != sha256(counts):
        raise ValidationError(f"Counts checksum mismatch in {case_id}")

    # Repeat every case in the same installed-package process. The deterministic
    # report excludes timestamps, so all three files must be byte-identical.
    first_hashes = (sha256(output), sha256(counts), sha256(report))
    filter_nexus_file(
        input_nexus,
        regions_path,
        output,
        counts,
        report_path=report,
        force=True,
    )
    second_hashes = (sha256(output), sha256(counts), sha256(report))
    if first_hashes != second_hashes:
        raise ValidationError(f"Repeat run was not deterministic in {case_id}")

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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all 1,000 synthetic cases.")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    synthetic_root = Path(__file__).resolve().parent
    cases_root = synthetic_root / "cases_1000"
    manifest_path = synthetic_root / "case_1000_manifest.tsv"
    oracle = load_oracle(repo_root / "validation" / "oracle" / "expected_rows.py")

    case_dirs = sorted(path for path in cases_root.iterdir() if path.is_dir())
    if len(case_dirs) != 1000:
        raise ValidationError(f"Expected 1,000 case directories, found {len(case_dirs)}")
    manifest_rows = read_tsv(manifest_path)
    manifest_by_id = {row["case_id"]: row for row in manifest_rows}
    if len(manifest_by_id) != 1000:
        raise ValidationError("Manifest does not contain 1,000 unique cases")

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="nexcision-synthetic-1000-fast-") as temp:
        work_root = Path(temp)
        rows: list[dict[str, object]] = []
        for index, case_dir in enumerate(case_dirs, start=1):
            rows.append(validate_case(case_dir, work_root, manifest_by_id[case_dir.name], oracle))
            if index % 50 == 0:
                print(f"Validated {index}/1000 cases...", flush=True)
    wall_seconds = time.perf_counter() - started

    args.results.parent.mkdir(parents=True, exist_ok=True)
    write_results(args.results, rows)

    runtimes = [float(row["runtime_seconds"]) for row in rows]
    family_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        family_counts[str(row["family"])] += 1
    aggregate = {
        "cases": len(rows),
        "cases_passed": sum(row["overall"] == "PASS" for row in rows),
        "cases_per_family": dict(sorted(family_counts.items())),
        "scenario_families": len(family_counts),
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
        "median_filter_runtime_seconds": statistics.median(runtimes),
        "maximum_filter_runtime_seconds": max(runtimes),
        "validation_wall_seconds": wall_seconds,
        "all_oracle_agreement": all(row["oracle_agreement"] == "PASS" for row in rows),
        "all_retained_rows_exact": all(row["retained_rows_exact"] == "PASS" for row in rows),
        "all_dimensions_correct": all(row["dimensions"] == "PASS" for row in rows),
        "all_region_counts_correct": all(row["region_counts"] == "PASS" for row in rows),
        "all_report_checksums_correct": all(row["report_checksums"] == "PASS" for row in rows),
        "all_repeat_runs_deterministic": all(row["repeat_determinism"] == "PASS" for row in rows),
        "nexcision_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "tested_mode": "installed wheel; in-process public core API",
        "results_sha256": sha256(args.results),
    }
    args.summary.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("PASS — all 1,000 synthetic correctness cases")
    print(f"Results: {args.results.resolve()}")
    print(f"Summary: {args.summary.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, ValueError, ValidationError) as exc:
        print("FAIL — 1,000-case synthetic validation", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        raise SystemExit(1)

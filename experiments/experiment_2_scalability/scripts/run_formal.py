#!/usr/bin/env python3
"""Generate and execute the formal Experiment 2 benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = {
    "series",
    "case_id",
    "taxa",
    "sites",
    "intervals",
    "geometry",
    "removal_fraction",
    "with_report",
    "warmups",
    "repeats",
    "design_note",
}

FIELDS = [
    "series",
    "case_id",
    "run_type",
    "run_order",
    "repeat",
    "with_report",
    "design_note",
    "taxa",
    "sites",
    "requested_intervals",
    "actual_intervals",
    "geometry",
    "requested_removal_fraction",
    "actual_removal_fraction",
    "returncode",
    "correct",
    "elapsed_seconds",
    "user_cpu_seconds",
    "system_cpu_seconds",
    "cpu_seconds",
    "cpu_efficiency",
    "peak_rss_bytes",
    "input_bytes",
    "regions_bytes",
    "output_bytes",
    "counts_bytes",
    "report_bytes",
    "throughput_input_mib_s",
    "expected_removed_rows",
    "expected_retained_rows",
    "observed_retained_rows",
    "observed_ntax",
    "observed_nchar",
    "filtered_sha256",
    "load1_before",
    "load5_before",
    "load15_before",
    "load1_after",
    "load5_after",
    "load15_after",
    "started_at_utc",
    "finished_at_utc",
]

INVENTORY_FIELDS = [
    "series",
    "case_id",
    "design_note",
    "taxa",
    "sites",
    "requested_intervals",
    "actual_intervals",
    "geometry",
    "requested_removal_fraction",
    "actual_removal_fraction",
    "with_report",
    "warmups",
    "repeats",
    "expected_removed_rows",
    "expected_retained_rows",
    "input_bytes",
    "regions_bytes",
]


def boolean(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError("Manifest has no header.")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Manifest is missing columns: {sorted(missing)}")
        rows = list(reader)

    if not rows:
        raise ValueError("Manifest contains no benchmark cases.")

    case_ids = [row["case_id"] for row in rows]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Every manifest case_id must be unique.")

    for row in rows:
        if int(row["taxa"]) < 2:
            raise ValueError(f"{row['case_id']}: taxa must be at least 2")
        if int(row["sites"]) < 2:
            raise ValueError(f"{row['case_id']}: sites must be at least 2")
        if int(row["intervals"]) < 1:
            raise ValueError(f"{row['case_id']}: intervals must be at least 1")
        if int(row["warmups"]) < 0 or int(row["repeats"]) < 1:
            raise ValueError(f"{row['case_id']}: invalid warmup/repeat counts")
        fraction = float(row["removal_fraction"])
        if not 0 < fraction < 1:
            raise ValueError(f"{row['case_id']}: removal_fraction must be 0–1")

    return rows


def write_tsv_header(path: Path, fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=fields, delimiter="\t").writeheader()
        handle.flush()
        os.fsync(handle.fileno())


def append_tsv(path: Path, fields: list[str], row: dict[str, Any]) -> None:
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writerow({field: row.get(field) for field in fields})
        handle.flush()
        os.fsync(handle.fileno())


def run_case(
    *,
    script_dir: Path,
    case_dir: Path,
    manifest_row: dict[str, str],
    run_type: str,
    run_order: int,
    repeat: int,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script_dir / "run_one.py"),
        "--case-dir",
        str(case_dir),
        "--repeat",
        str(repeat),
    ]
    if boolean(manifest_row["with_report"]):
        command.append("--with-report")

    before_load = os.getloadavg()
    started = datetime.now(timezone.utc)
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    finished = datetime.now(timezone.utc)
    after_load = os.getloadavg()

    if not completed.stdout.strip():
        raise RuntimeError(
            f"No metrics for {manifest_row['case_id']} {run_type} {repeat}: "
            f"{completed.stderr.strip()}"
        )

    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    cpu_seconds = float(payload["user_cpu_seconds"]) + float(
        payload["system_cpu_seconds"]
    )
    elapsed = float(payload["elapsed_seconds"])

    metadata = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    payload.update(
        {
            "series": manifest_row["series"],
            "run_type": run_type,
            "run_order": run_order,
            "design_note": manifest_row["design_note"],
            "taxa": metadata["taxa"],
            "sites": metadata["sites"],
            "requested_intervals": metadata["requested_intervals"],
            "actual_intervals": metadata["actual_intervals"],
            "geometry": metadata["geometry"],
            "requested_removal_fraction": metadata[
                "requested_removal_fraction"
            ],
            "actual_removal_fraction": metadata["actual_removal_fraction"],
            "cpu_seconds": cpu_seconds,
            "cpu_efficiency": cpu_seconds / elapsed if elapsed else None,
            "load1_before": before_load[0],
            "load5_before": before_load[1],
            "load15_before": before_load[2],
            "load1_after": after_load[0],
            "load5_after": after_load[1],
            "load15_after": after_load[2],
            "started_at_utc": started.isoformat(),
            "finished_at_utc": finished.isoformat(),
        }
    )

    if completed.returncode != 0 or not payload["correct"]:
        raise RuntimeError(
            f"Correctness failure for {manifest_row['case_id']} "
            f"{run_type} {repeat}: {payload.get('stderr', '')}"
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--measured-results", type=Path, required=True)
    parser.add_argument("--warmup-results", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260722)
    args = parser.parse_args()

    rows = read_manifest(args.manifest)
    script_dir = Path(__file__).resolve().parent
    args.work_dir.mkdir(parents=True, exist_ok=True)
    write_tsv_header(args.measured_results, FIELDS)
    write_tsv_header(args.warmup_results, FIELDS)
    write_tsv_header(args.inventory, INVENTORY_FIELDS)

    print(f"Generating {len(rows)} formal benchmark cases...", flush=True)
    for index, row in enumerate(rows, start=1):
        case_dir = args.work_dir / row["case_id"]
        command = [
            sys.executable,
            str(script_dir / "generate_case.py"),
            "--case-id",
            row["case_id"],
            "--taxa",
            row["taxa"],
            "--sites",
            row["sites"],
            "--intervals",
            row["intervals"],
            "--geometry",
            row["geometry"],
            "--removal-fraction",
            row["removal_fraction"],
            "--output-dir",
            str(case_dir),
        ]
        completed = subprocess.run(
            command, text=True, capture_output=True, check=True
        )
        metadata = json.loads(completed.stdout.strip().splitlines()[-1])
        inventory = {
            "series": row["series"],
            "case_id": row["case_id"],
            "design_note": row["design_note"],
            "with_report": boolean(row["with_report"]),
            "warmups": int(row["warmups"]),
            "repeats": int(row["repeats"]),
            **metadata,
        }
        append_tsv(args.inventory, INVENTORY_FIELDS, inventory)
        print(
            f"[{index}/{len(rows)}] generated {row['case_id']}: "
            f"{metadata['input_bytes'] / (1024**3):.3f} GiB, "
            f"{metadata['actual_intervals']} intervals",
            flush=True,
        )

    # Flush generated files before warm-up runs. We intentionally do not drop
    # the page cache: the formal measurements characterize warm-cache
    # application performance on a controlled node.
    if hasattr(os, "sync"):
        os.sync()

    warmup_tasks: list[tuple[dict[str, str], int]] = []
    for row in rows:
        for repeat in range(1, int(row["warmups"]) + 1):
            warmup_tasks.append((row, repeat))

    print(f"Running {len(warmup_tasks)} unreported warm-up executions...", flush=True)
    for run_order, (row, repeat) in enumerate(warmup_tasks, start=1):
        payload = run_case(
            script_dir=script_dir,
            case_dir=args.work_dir / row["case_id"],
            manifest_row=row,
            run_type="warmup",
            run_order=run_order,
            repeat=repeat,
        )
        append_tsv(args.warmup_results, FIELDS, payload)
        print(
            f"[warm-up {run_order}/{len(warmup_tasks)}] PASS {row['case_id']}: "
            f"{payload['elapsed_seconds']:.3f} s, "
            f"{payload['peak_rss_bytes'] / (1024**3):.3f} GiB",
            flush=True,
        )

    measured_tasks: list[tuple[dict[str, str], int]] = []
    for row in rows:
        for repeat in range(1, int(row["repeats"]) + 1):
            measured_tasks.append((row, repeat))
    random.Random(args.seed).shuffle(measured_tasks)

    print(
        f"Running {len(measured_tasks)} measured executions in randomized order...",
        flush=True,
    )
    checksums: dict[str, str] = {}
    for run_order, (row, repeat) in enumerate(measured_tasks, start=1):
        payload = run_case(
            script_dir=script_dir,
            case_dir=args.work_dir / row["case_id"],
            manifest_row=row,
            run_type="measured",
            run_order=run_order,
            repeat=repeat,
        )
        checksum = str(payload["filtered_sha256"])
        previous = checksums.setdefault(row["case_id"], checksum)
        if checksum != previous:
            raise RuntimeError(
                f"Non-deterministic output checksum for {row['case_id']}: "
                f"{previous} != {checksum}"
            )
        append_tsv(args.measured_results, FIELDS, payload)
        print(
            f"[{run_order}/{len(measured_tasks)}] PASS {row['case_id']} "
            f"repeat {repeat}: {payload['elapsed_seconds']:.3f} s, "
            f"{payload['peak_rss_bytes'] / (1024**3):.3f} GiB",
            flush=True,
        )

    print(
        f"Formal benchmark complete: {len(measured_tasks)}/{len(measured_tasks)} "
        "measured runs correct",
        flush=True,
    )
    print(f"Measured results: {args.measured_results}", flush=True)
    print(f"Warm-up results: {args.warmup_results}", flush=True)
    print(f"Case inventory: {args.inventory}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

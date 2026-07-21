#!/usr/bin/env python3
"""Generate and execute the Experiment 2 instrumentation pilot."""

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
from pathlib import Path

FIELDS = [
    "case_id",
    "repeat",
    "with_report",
    "returncode",
    "correct",
    "elapsed_seconds",
    "user_cpu_seconds",
    "system_cpu_seconds",
    "peak_rss_bytes",
    "input_bytes",
    "regions_bytes",
    "output_bytes",
    "throughput_input_mib_s",
    "expected_removed_rows",
    "expected_retained_rows",
    "observed_retained_rows",
    "observed_ntax",
    "observed_nchar",
    "filtered_sha256",
]


def boolean(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260722)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.results.parent.mkdir(parents=True, exist_ok=True)

    with args.manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    tasks: list[tuple[dict[str, str], int]] = []
    for row in rows:
        case_dir = args.work_dir / row["case_id"]
        generate_command = [
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
        subprocess.run(generate_command, check=True)
        for repeat in range(1, int(row["repeats"]) + 1):
            tasks.append((row, repeat))

    random.Random(args.seed).shuffle(tasks)
    results: list[dict[str, object]] = []

    for index, (row, repeat) in enumerate(tasks, start=1):
        case_dir = args.work_dir / row["case_id"]
        command = [
            sys.executable,
            str(script_dir / "run_one.py"),
            "--case-dir",
            str(case_dir),
            "--repeat",
            str(repeat),
        ]
        if boolean(row["with_report"]):
            command.append("--with-report")

        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if not completed.stdout.strip():
            raise RuntimeError(
                f"Benchmark produced no metrics for {row['case_id']} repeat {repeat}: "
                f"{completed.stderr}"
            )
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        results.append(payload)
        status = "PASS" if payload["correct"] else "FAIL"
        print(
            f"[{index}/{len(tasks)}] {status} {row['case_id']} repeat {repeat}: "
            f"{payload['elapsed_seconds']:.4f} s, "
            f"{payload['peak_rss_bytes'] / (1024**2):.1f} MiB"
        )
        if completed.returncode != 0 or not payload["correct"]:
            raise RuntimeError(
                f"Benchmark correctness failure for {row['case_id']} repeat {repeat}"
            )

    with args.results.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        for result in results:
            writer.writerow({field: result.get(field) for field in FIELDS})

    print(f"Pilot complete: {len(results)}/{len(results)} runs correct")
    print(f"Results written to: {args.results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

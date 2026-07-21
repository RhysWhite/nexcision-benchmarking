#!/usr/bin/env python3
"""Summarize the formal Experiment 2 measured results."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

SUMMARY_FIELDS = [
    "series",
    "case_id",
    "design_note",
    "n_runs",
    "all_correct",
    "deterministic_output",
    "taxa",
    "sites",
    "actual_intervals",
    "geometry",
    "actual_removal_fraction",
    "with_report",
    "input_bytes",
    "input_gib",
    "output_bytes",
    "elapsed_median_seconds",
    "elapsed_q1_seconds",
    "elapsed_q3_seconds",
    "elapsed_iqr_seconds",
    "peak_rss_median_bytes",
    "peak_rss_q1_bytes",
    "peak_rss_q3_bytes",
    "peak_rss_median_gib",
    "throughput_median_mib_s",
    "throughput_q1_mib_s",
    "throughput_q3_mib_s",
    "cpu_seconds_median",
    "cpu_efficiency_median",
]


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def percentile(values: list[float], probability: float) -> float:
    """Return a linearly interpolated percentile (R/NumPy type 7)."""

    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate a percentile of an empty list.")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def metrics(values: list[float]) -> tuple[float, float, float]:
    return (
        statistics.median(values),
        percentile(values, 0.25),
        percentile(values, 0.75),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--summary-tsv", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    args = parser.parse_args()

    with args.results.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise ValueError("Measured results table contains no runs.")

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["case_id"]].append(row)

    summaries: list[dict[str, Any]] = []
    for case_id, group in groups.items():
        first = group[0]
        elapsed = [float(row["elapsed_seconds"]) for row in group]
        peak = [float(row["peak_rss_bytes"]) for row in group]
        throughput = [float(row["throughput_input_mib_s"]) for row in group]
        cpu_seconds = [float(row["cpu_seconds"]) for row in group]
        cpu_efficiency = [float(row["cpu_efficiency"]) for row in group]

        elapsed_median, elapsed_q1, elapsed_q3 = metrics(elapsed)
        peak_median, peak_q1, peak_q3 = metrics(peak)
        throughput_median, throughput_q1, throughput_q3 = metrics(throughput)

        checksums = {row["filtered_sha256"] for row in group}
        all_correct = all(truthy(row["correct"]) for row in group)
        input_bytes = int(first["input_bytes"])

        summaries.append(
            {
                "series": first["series"],
                "case_id": case_id,
                "design_note": first["design_note"],
                "n_runs": len(group),
                "all_correct": all_correct,
                "deterministic_output": len(checksums) == 1,
                "taxa": int(first["taxa"]),
                "sites": int(first["sites"]),
                "actual_intervals": int(first["actual_intervals"]),
                "geometry": first["geometry"],
                "actual_removal_fraction": float(first["actual_removal_fraction"]),
                "with_report": truthy(first["with_report"]),
                "input_bytes": input_bytes,
                "input_gib": input_bytes / (1024**3),
                "output_bytes": int(first["output_bytes"]),
                "elapsed_median_seconds": elapsed_median,
                "elapsed_q1_seconds": elapsed_q1,
                "elapsed_q3_seconds": elapsed_q3,
                "elapsed_iqr_seconds": elapsed_q3 - elapsed_q1,
                "peak_rss_median_bytes": peak_median,
                "peak_rss_q1_bytes": peak_q1,
                "peak_rss_q3_bytes": peak_q3,
                "peak_rss_median_gib": peak_median / (1024**3),
                "throughput_median_mib_s": throughput_median,
                "throughput_q1_mib_s": throughput_q1,
                "throughput_q3_mib_s": throughput_q3,
                "cpu_seconds_median": statistics.median(cpu_seconds),
                "cpu_efficiency_median": statistics.median(cpu_efficiency),
            }
        )

    summaries.sort(key=lambda row: (str(row["series"]), str(row["case_id"])))
    args.summary_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_tsv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(summaries)

    payload = {
        "measured_runs": len(rows),
        "configurations": len(summaries),
        "all_runs_correct": all(truthy(row["correct"]) for row in rows),
        "all_outputs_deterministic": all(
            bool(summary["deterministic_output"]) for summary in summaries
        ),
        "series": {
            series: sum(1 for summary in summaries if summary["series"] == series)
            for series in sorted({str(summary["series"]) for summary in summaries})
        },
        "quantile_method": "linear interpolation, type 7",
        "summary_tsv": str(args.summary_tsv),
    }
    args.summary_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    if not payload["all_runs_correct"]:
        raise RuntimeError("At least one formal benchmark run failed correctness checks.")
    if not payload["all_outputs_deterministic"]:
        raise RuntimeError("At least one configuration produced different checksums.")

    print(
        f"Formal summary complete: {len(rows)} runs across {len(summaries)} configurations"
    )
    print(f"Summary TSV: {args.summary_tsv}")
    print(f"Summary JSON: {args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

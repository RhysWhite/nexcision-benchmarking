#!/usr/bin/env python3
"""Reproduce NEXCISION Experiment 2 derived tables and manuscript figures."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments" / "experiment_2_scalability"
FORMAL = EXP / "results" / "formal"
DERIVED = FORMAL / "derived"
FIGURES = ROOT / "manuscript" / "figures" / "experiment_2"
TABLES = ROOT / "manuscript" / "tables"
EXPECTED_WHEEL_SHA256 = "f980aa7e1f4b5ef67ebe10b4117a07af3405ee0cd3805c1d2d9e936a284689d4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--job-id",
        default="2432330",
        help="Slurm job identifier used in formal result filenames.",
    )
    return parser.parse_args()


def load_inputs(job_id: str):
    paths = {
        "measured": FORMAL / f"formal_measured-{job_id}.tsv",
        "summary": FORMAL / f"formal_summary-{job_id}.tsv",
        "start": FORMAL / f"system_info-start-{job_id}.json",
        "end": FORMAL / f"system_info-end-{job_id}.json",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing required source files:\n" + "\n".join(missing))

    measured = pd.read_csv(paths["measured"], sep="\t")
    summary = pd.read_csv(paths["summary"], sep="\t")
    with paths["start"].open() as handle:
        system_start = json.load(handle)
    with paths["end"].open() as handle:
        system_end = json.load(handle)
    return measured, summary, system_start, system_end


def configuration(summary: pd.DataFrame, case_id: str) -> pd.Series:
    rows = summary.loc[summary["case_id"] == case_id]
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one summary row for {case_id!r}.")
    return rows.iloc[0]


def save_figure(stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIGURES / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.savefig(FIGURES / f"{stem}.svg", bbox_inches="tight")
    plt.close()


def nonnegative_errors(median, q1, q3):
    median = np.asarray(median, dtype=float)
    q1 = np.asarray(q1, dtype=float)
    q3 = np.asarray(q3, dtype=float)
    return np.vstack([
        np.maximum(0, median - q1),
        np.maximum(0, q3 - median),
    ])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_bool(series: pd.Series, name: str) -> pd.Series:
    """Parse a Boolean column without treating the string 'False' as truthy."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    mapping = {
        "1": True,
        "true": True,
        "yes": True,
        "y": True,
        "0": False,
        "false": False,
        "no": False,
        "n": False,
    }
    normalized = series.astype(str).str.strip().str.lower().map(mapping)
    if normalized.isna().any():
        bad = sorted(set(series.loc[normalized.isna()].astype(str)))
        raise SystemExit(f"Invalid Boolean values in {name}: {bad}")
    return normalized.astype(bool)


def percentile(values: list[float], probability: float) -> float:
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


def close_enough(observed: float, expected: float) -> bool:
    return math.isclose(float(observed), float(expected), rel_tol=1e-12, abs_tol=1e-9)


def validate_source_record(
    measured: pd.DataFrame,
    summary: pd.DataFrame,
    system_start: dict,
    system_end: dict,
    job_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_measured = {
        "series", "case_id", "repeat", "returncode", "correct",
        "elapsed_seconds", "peak_rss_bytes", "throughput_input_mib_s",
        "cpu_seconds", "cpu_efficiency", "filtered_sha256", "taxa", "sites",
        "actual_intervals", "geometry", "actual_removal_fraction",
        "with_report", "input_bytes", "output_bytes", "expected_retained_rows",
        "observed_retained_rows", "observed_ntax", "observed_nchar",
        "run_order", "load1_before", "started_at_utc", "finished_at_utc",
    }
    required_summary = {
        "series", "case_id", "n_runs", "all_correct",
        "deterministic_output", "taxa", "sites", "actual_intervals",
        "geometry", "actual_removal_fraction", "with_report", "input_bytes",
        "input_gib", "output_bytes", "elapsed_median_seconds",
        "elapsed_q1_seconds", "elapsed_q3_seconds", "elapsed_iqr_seconds",
        "peak_rss_median_bytes", "peak_rss_q1_bytes", "peak_rss_q3_bytes",
        "peak_rss_median_gib", "throughput_median_mib_s",
        "throughput_q1_mib_s", "throughput_q3_mib_s",
        "cpu_seconds_median", "cpu_efficiency_median",
    }
    missing_measured = required_measured - set(measured.columns)
    missing_summary = required_summary - set(summary.columns)
    if missing_measured:
        raise SystemExit(f"Measured table is missing columns: {sorted(missing_measured)}")
    if missing_summary:
        raise SystemExit(f"Summary table is missing columns: {sorted(missing_summary)}")

    measured = measured.copy()
    summary = summary.copy()
    measured["correct"] = normalized_bool(measured["correct"], "measured.correct")
    measured["with_report"] = normalized_bool(
        measured["with_report"], "measured.with_report"
    )
    summary["all_correct"] = normalized_bool(
        summary["all_correct"], "summary.all_correct"
    )
    summary["deterministic_output"] = normalized_bool(
        summary["deterministic_output"], "summary.deterministic_output"
    )
    summary["with_report"] = normalized_bool(
        summary["with_report"], "summary.with_report"
    )

    if len(measured) != 105:
        raise SystemExit(f"Expected 105 measured runs; observed {len(measured)}.")
    if len(summary) != 21:
        raise SystemExit(f"Expected 21 configurations; observed {len(summary)}.")
    if measured["case_id"].nunique() != 21:
        raise SystemExit("Measured table does not contain exactly 21 unique case IDs.")
    if summary["case_id"].nunique() != 21:
        raise SystemExit("Summary table does not contain exactly 21 unique case IDs.")
    if not (measured["returncode"] == 0).all():
        raise SystemExit("At least one measured run has a non-zero return code.")
    if not measured["correct"].all():
        raise SystemExit("At least one measured run failed correctness checks.")
    if not summary["all_correct"].all():
        raise SystemExit("At least one summary configuration is not fully correct.")
    if not summary["deterministic_output"].all():
        raise SystemExit("At least one configuration has non-deterministic output.")

    group_sizes = measured.groupby("case_id").size()
    if not (group_sizes == 5).all():
        raise SystemExit(
            "Every configuration must contain five measured repetitions; "
            f"observed {group_sizes.to_dict()}."
        )
    for case_id, group in measured.groupby("case_id"):
        repeats = sorted(group["repeat"].astype(int).tolist())
        if repeats != [1, 2, 3, 4, 5]:
            raise SystemExit(f"Unexpected repeat identifiers for {case_id}: {repeats}")
        if group["filtered_sha256"].nunique() != 1:
            raise SystemExit(f"Filtered output was not deterministic for {case_id}.")
        if not (
            group["observed_retained_rows"].astype(int)
            == group["expected_retained_rows"].astype(int)
        ).all():
            raise SystemExit(f"Retained-row mismatch in {case_id}.")
        if not (
            group["observed_nchar"].astype(int)
            == group["expected_retained_rows"].astype(int)
        ).all():
            raise SystemExit(f"nchar mismatch in {case_id}.")
        if not (
            group["observed_ntax"].astype(int) == group["taxa"].astype(int)
        ).all():
            raise SystemExit(f"ntax mismatch in {case_id}.")

    # Independently verify every configuration summary from the measured table.
    summary_by_case = summary.set_index("case_id")
    for case_id, group in measured.groupby("case_id"):
        if case_id not in summary_by_case.index:
            raise SystemExit(f"Summary is missing configuration {case_id}.")
        row = summary_by_case.loc[case_id]
        elapsed = group["elapsed_seconds"].astype(float).tolist()
        peak = group["peak_rss_bytes"].astype(float).tolist()
        throughput = group["throughput_input_mib_s"].astype(float).tolist()
        cpu_seconds = group["cpu_seconds"].astype(float).tolist()
        cpu_efficiency = group["cpu_efficiency"].astype(float).tolist()

        expected_values = {
            "n_runs": len(group),
            "elapsed_median_seconds": statistics.median(elapsed),
            "elapsed_q1_seconds": percentile(elapsed, 0.25),
            "elapsed_q3_seconds": percentile(elapsed, 0.75),
            "peak_rss_median_bytes": statistics.median(peak),
            "peak_rss_q1_bytes": percentile(peak, 0.25),
            "peak_rss_q3_bytes": percentile(peak, 0.75),
            "throughput_median_mib_s": statistics.median(throughput),
            "throughput_q1_mib_s": percentile(throughput, 0.25),
            "throughput_q3_mib_s": percentile(throughput, 0.75),
            "cpu_seconds_median": statistics.median(cpu_seconds),
            "cpu_efficiency_median": statistics.median(cpu_efficiency),
        }
        expected_values["elapsed_iqr_seconds"] = (
            expected_values["elapsed_q3_seconds"]
            - expected_values["elapsed_q1_seconds"]
        )
        expected_values["peak_rss_median_gib"] = (
            expected_values["peak_rss_median_bytes"] / (1024**3)
        )
        for column, expected in expected_values.items():
            if not close_enough(row[column], expected):
                raise SystemExit(
                    f"Stored summary disagrees with measured data for "
                    f"{case_id}.{column}: observed {row[column]!r}, "
                    f"expected {expected!r}."
                )

        first = group.iloc[0]
        constant_values = {
            "series": first["series"],
            "taxa": int(first["taxa"]),
            "sites": int(first["sites"]),
            "actual_intervals": int(first["actual_intervals"]),
            "geometry": first["geometry"],
            "actual_removal_fraction": float(first["actual_removal_fraction"]),
            "with_report": bool(first["with_report"]),
            "input_bytes": int(first["input_bytes"]),
            "input_gib": int(first["input_bytes"]) / (1024**3),
            "output_bytes": int(first["output_bytes"]),
        }
        for column, expected in constant_values.items():
            observed = row[column]
            if isinstance(expected, float):
                valid = close_enough(observed, expected)
            else:
                valid = observed == expected
            if not valid:
                raise SystemExit(
                    f"Stored summary metadata disagrees for {case_id}.{column}: "
                    f"observed {observed!r}, expected {expected!r}."
                )

    # Validate the two system snapshots and the frozen software artifact.
    for label, snapshot in [("start", system_start), ("end", system_end)]:
        observed_job = str(snapshot.get("environment", {}).get("SLURM_JOB_ID"))
        if observed_job != str(job_id):
            raise SystemExit(
                f"{label} system snapshot records Slurm job {observed_job}, "
                f"expected {job_id}."
            )
        wheel = snapshot.get("software_wheel") or {}
        if wheel.get("sha256") != EXPECTED_WHEEL_SHA256:
            raise SystemExit(
                f"{label} system snapshot has an unexpected wheel checksum."
            )
        version = (
            snapshot.get("commands", {})
            .get("nexcise_version", {})
            .get("stdout")
        )
        if version != "NEXCISION 0.1.0":
            raise SystemExit(
                f"{label} system snapshot records an unexpected version: {version!r}."
            )

    start_host = (
        system_start.get("commands", {}).get("hostname", {}).get("stdout")
    )
    end_host = system_end.get("commands", {}).get("hostname", {}).get("stdout")
    if not start_host or start_host != end_host:
        raise SystemExit("Start and end system snapshots do not record the same host.")

    start_commit = (
        system_start.get("commands", {}).get("git_commit", {}).get("stdout")
    )
    end_commit = system_end.get("commands", {}).get("git_commit", {}).get("stdout")
    if not start_commit or start_commit != end_commit:
        raise SystemExit("Start and end system snapshots do not record the same commit.")

    local_wheel = ROOT / "software" / "nexcision-0.1.0-py3-none-any.whl"
    if sha256_file(local_wheel) != EXPECTED_WHEEL_SHA256:
        raise SystemExit("The repository wheel does not match the frozen checksum.")

    start_time = pd.Timestamp(system_start["captured_at_utc"])
    end_time = pd.Timestamp(system_end["captured_at_utc"])
    if not start_time < end_time:
        raise SystemExit("System snapshot timestamps are not ordered.")

    measured_start = pd.to_datetime(measured["started_at_utc"], utc=True).min()
    measured_end = pd.to_datetime(measured["finished_at_utc"], utc=True).max()
    if measured_start < start_time or measured_end > end_time:
        raise SystemExit("Measured run timestamps fall outside the system snapshots.")

    return measured, summary


def main() -> int:
    args = parse_args()
    measured, summary, system_start, system_end = load_inputs(args.job_id)
    measured, summary = validate_source_record(
        measured, summary, system_start, system_end, args.job_id
    )

    DERIVED.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    grouped = measured.groupby(["series", "case_id"], sort=False)
    qc = grouped.agg(
        n_runs=("elapsed_seconds", "size"),
        all_correct=("correct", "all"),
        elapsed_mean_seconds=("elapsed_seconds", "mean"),
        elapsed_sd_seconds=("elapsed_seconds", "std"),
        elapsed_median_seconds=("elapsed_seconds", "median"),
        elapsed_min_seconds=("elapsed_seconds", "min"),
        elapsed_max_seconds=("elapsed_seconds", "max"),
        peak_rss_mean_bytes=("peak_rss_bytes", "mean"),
        peak_rss_sd_bytes=("peak_rss_bytes", "std"),
        peak_rss_median_bytes=("peak_rss_bytes", "median"),
        cpu_efficiency_mean=("cpu_efficiency", "mean"),
        load1_before_mean=("load1_before", "mean"),
        load1_before_max=("load1_before", "max"),
    ).reset_index()
    qc["elapsed_cv_percent"] = (
        qc["elapsed_sd_seconds"] / qc["elapsed_mean_seconds"] * 100
    )
    qc["peak_rss_cv_percent"] = (
        qc["peak_rss_sd_bytes"] / qc["peak_rss_mean_bytes"] * 100
    )
    qc["peak_rss_median_gib"] = qc["peak_rss_median_bytes"] / (1024**3)
    qc.to_csv(
        DERIVED / "experiment2_qc_by_configuration.tsv",
        sep="\t",
        index=False,
    )

    input_size = summary.loc[summary["series"] == "input_size"].sort_values("input_gib")
    x = input_size["input_gib"].to_numpy(dtype=float)
    runtime = input_size["elapsed_median_seconds"].to_numpy(dtype=float)
    memory = input_size["peak_rss_median_bytes"].to_numpy(dtype=float) / (1024**3)

    runtime_coef = np.polyfit(x, runtime, 1)
    runtime_fit = np.polyval(runtime_coef, x)
    runtime_r2 = 1 - np.sum((runtime - runtime_fit) ** 2) / np.sum(
        (runtime - runtime.mean()) ** 2
    )

    memory_coef = np.polyfit(x, memory, 1)
    memory_fit = np.polyval(memory_coef, x)
    memory_r2 = 1 - np.sum((memory - memory_fit) ** 2) / np.sum(
        (memory - memory.mean()) ** 2
    )

    scale_mask = x >= 0.09
    runtime_log_exponent = np.polyfit(
        np.log10(x[scale_mask]), np.log10(runtime[scale_mask]), 1
    )[0]
    memory_log_exponent = np.polyfit(
        np.log10(x[scale_mask]), np.log10(memory[scale_mask]), 1
    )[0]

    one_interval = configuration(summary, "intervals_000001")
    hundred_thousand = configuration(summary, "intervals_100000")
    interval_runtime_increase = (
        hundred_thousand["elapsed_median_seconds"]
        / one_interval["elapsed_median_seconds"]
        - 1
    ) * 100
    interval_memory_increase = (
        hundred_thousand["peak_rss_median_bytes"]
        / one_interval["peak_rss_median_bytes"]
        - 1
    ) * 100

    geometry = summary.loc[summary["series"] == "interval_geometry"]
    geometry_runtime_spread = (
        geometry["elapsed_median_seconds"].max()
        / geometry["elapsed_median_seconds"].min()
        - 1
    ) * 100

    shape = summary.loc[summary["series"] == "matrix_shape"].set_index("case_id")
    tall_vs_wide = (
        shape.loc["shape_tall", "elapsed_median_seconds"]
        / shape.loc["shape_wide", "elapsed_median_seconds"]
    )

    report_off = configuration(summary, "report_off")
    report_on = configuration(summary, "report_on")
    report_overhead = (
        report_on["elapsed_median_seconds"]
        / report_off["elapsed_median_seconds"]
        - 1
    ) * 100

    median_cv_excluding_small = qc.loc[
        qc["case_id"] != "size_010mb", "elapsed_cv_percent"
    ].median()
    max_cv_excluding_small = qc.loc[
        qc["case_id"] != "size_010mb", "elapsed_cv_percent"
    ].max()

    measured = measured.copy()
    measured["case_median"] = measured.groupby("case_id")[
        "elapsed_seconds"
    ].transform("median")
    measured["runtime_ratio_to_case_median"] = (
        measured["elapsed_seconds"] / measured["case_median"]
    )
    run_order_correlation = measured[
        ["run_order", "runtime_ratio_to_case_median"]
    ].corr().iloc[0, 1]
    load_correlation = measured[
        ["load1_before", "runtime_ratio_to_case_median"]
    ].corr().iloc[0, 1]

    start = pd.Timestamp(system_start["captured_at_utc"])
    end = pd.Timestamp(system_end["captured_at_utc"])
    duration_minutes = (end - start).total_seconds() / 60
    scratch_growth_gib = (
        system_start["storage_at_repository"]["free_bytes"]
        - system_end["storage_at_repository"]["free_bytes"]
    ) / (1024**3)

    key_results = pd.DataFrame(
        [
            ["Measured executions", len(measured), "runs"],
            ["Correct executions", int(measured["correct"].sum()), "runs"],
            [
                "Deterministic configurations",
                int(summary["deterministic_output"].sum()),
                "of 21",
            ],
            ["Formal benchmark duration", duration_minutes, "minutes"],
            ["Scratch-space growth during run", scratch_growth_gib, "GiB"],
            ["Runtime slope", runtime_coef[0], "seconds per GiB input"],
            ["Runtime linear-model R²", runtime_r2, ""],
            [
                "Runtime log-log exponent (>=100 MB)",
                runtime_log_exponent,
                "",
            ],
            ["Peak-memory slope", memory_coef[0], "GiB RSS per GiB input"],
            ["Peak-memory linear-model R²", memory_r2, ""],
            [
                "Peak-memory log-log exponent (>=100 MB)",
                memory_log_exponent,
                "",
            ],
            [
                "1 to 100,000 interval runtime increase",
                interval_runtime_increase,
                "%",
            ],
            [
                "1 to 100,000 interval memory increase",
                interval_memory_increase,
                "%",
            ],
            ["Interval-geometry runtime spread", geometry_runtime_spread, "%"],
            ["Tall versus wide runtime ratio", tall_vs_wide, "fold"],
            ["Provenance-report runtime overhead", report_overhead, "%"],
            [
                "Median runtime CV, excluding 10 MB",
                median_cv_excluding_small,
                "%",
            ],
            [
                "Maximum runtime CV, excluding 10 MB",
                max_cv_excluding_small,
                "%",
            ],
            [
                "Run-order correlation with normalized runtime",
                run_order_correlation,
                "Pearson r",
            ],
            [
                "Node-load correlation with normalized runtime",
                load_correlation,
                "Pearson r",
            ],
        ],
        columns=["metric", "value", "unit"],
    )
    key_results.to_csv(
        DERIVED / "experiment2_key_results.tsv",
        sep="\t",
        index=False,
    )
    key_results.to_csv(
        TABLES / "experiment2_key_results.tsv",
        sep="\t",
        index=False,
    )

    # Figure 2A: runtime scaling
    plt.figure(figsize=(7.2, 5.2))
    plt.errorbar(
        input_size["input_gib"],
        input_size["elapsed_median_seconds"],
        yerr=nonnegative_errors(
            input_size["elapsed_median_seconds"],
            input_size["elapsed_q1_seconds"],
            input_size["elapsed_q3_seconds"],
        ),
        marker="o",
        capsize=4,
    )
    fit_x = np.linspace(x.min(), x.max(), 200)
    plt.plot(fit_x, runtime_coef[0] * fit_x + runtime_coef[1], linestyle="--")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Input size (GiB)")
    plt.ylabel("Median elapsed time (seconds)")
    plt.title("NEXCISION runtime scales near-linearly with input size")
    for _, row in input_size.iterrows():
        plt.annotate(
            row["case_id"].replace("size_", ""),
            (row["input_gib"], row["elapsed_median_seconds"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )
    save_figure("figure_2A_runtime_scaling")

    # Figure 2B: memory scaling
    plt.figure(figsize=(7.2, 5.2))
    median_memory = input_size["peak_rss_median_bytes"] / (1024**3)
    q1_memory = input_size["peak_rss_q1_bytes"] / (1024**3)
    q3_memory = input_size["peak_rss_q3_bytes"] / (1024**3)
    plt.errorbar(
        input_size["input_gib"],
        median_memory,
        yerr=nonnegative_errors(median_memory, q1_memory, q3_memory),
        marker="o",
        capsize=4,
    )
    plt.plot(fit_x, memory_coef[0] * fit_x + memory_coef[1], linestyle="--")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Input size (GiB)")
    plt.ylabel("Median peak RSS (GiB)")
    plt.title("Peak memory increases proportionally with input size")
    for _, row in input_size.iterrows():
        plt.annotate(
            row["case_id"].replace("size_", ""),
            (row["input_gib"], row["peak_rss_median_bytes"] / (1024**3)),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )
    save_figure("figure_2B_memory_scaling")

    # Figure 2C: matrix shape
    shape_order = ["shape_tall", "shape_balanced", "shape_wide"]
    shape_plot = summary.set_index("case_id").loc[shape_order].reset_index()
    shape_labels = ["Tall\n64 × 3.5M", "Balanced\n512 × 500k", "Wide\n8192 × 32k"]
    plt.figure(figsize=(7.2, 5.2))
    plt.bar(shape_labels, shape_plot["elapsed_median_seconds"])
    plt.errorbar(
        range(len(shape_plot)),
        shape_plot["elapsed_median_seconds"],
        yerr=nonnegative_errors(
            shape_plot["elapsed_median_seconds"],
            shape_plot["elapsed_q1_seconds"],
            shape_plot["elapsed_q3_seconds"],
        ),
        fmt="none",
        capsize=4,
    )
    plt.ylabel("Median elapsed time (seconds)")
    plt.xlabel("Matrix shape (taxa × site rows)")
    plt.title("Row count strongly affects runtime at similar file size")
    save_figure("figure_2C_matrix_shape")

    # Figure 2D: interval count
    intervals = summary.loc[
        summary["series"] == "interval_count"
    ].sort_values("actual_intervals")
    plt.figure(figsize=(7.2, 5.2))
    plt.errorbar(
        intervals["actual_intervals"],
        intervals["elapsed_median_seconds"],
        yerr=nonnegative_errors(
            intervals["elapsed_median_seconds"],
            intervals["elapsed_q1_seconds"],
            intervals["elapsed_q3_seconds"],
        ),
        marker="o",
        capsize=4,
    )
    plt.xscale("log")
    plt.xlabel("Number of supplied intervals")
    plt.ylabel("Median elapsed time (seconds)")
    plt.title("Runtime is only modestly affected by interval count")
    save_figure("figure_2D_interval_count")

    # Supplementary Figure S2A: interval geometry
    geometry_order = [
        "geometry_disjoint",
        "geometry_adjacent",
        "geometry_overlapping",
        "geometry_nested",
    ]
    geometry_plot = summary.set_index("case_id").loc[geometry_order].reset_index()
    plt.figure(figsize=(7.2, 5.2))
    plt.bar(
        ["Disjoint", "Adjacent", "Overlapping", "Nested"],
        geometry_plot["elapsed_median_seconds"],
    )
    plt.errorbar(
        range(len(geometry_plot)),
        geometry_plot["elapsed_median_seconds"],
        yerr=nonnegative_errors(
            geometry_plot["elapsed_median_seconds"],
            geometry_plot["elapsed_q1_seconds"],
            geometry_plot["elapsed_q3_seconds"],
        ),
        fmt="none",
        capsize=4,
    )
    plt.ylabel("Median elapsed time (seconds)")
    plt.xlabel("Interval geometry")
    plt.title("Interval arrangement has little effect on runtime")
    save_figure("figure_S2A_interval_geometry")

    # Supplementary Figure S2B: provenance overhead
    provenance = summary.loc[summary["series"] == "provenance"].set_index(
        "case_id"
    ).loc[["report_off", "report_on"]].reset_index()
    plt.figure(figsize=(6.2, 5.2))
    plt.bar(["Report off", "Report on"], provenance["elapsed_median_seconds"])
    plt.errorbar(
        range(len(provenance)),
        provenance["elapsed_median_seconds"],
        yerr=nonnegative_errors(
            provenance["elapsed_median_seconds"],
            provenance["elapsed_q1_seconds"],
            provenance["elapsed_q3_seconds"],
        ),
        fmt="none",
        capsize=4,
    )
    plt.ylabel("Median elapsed time (seconds)")
    plt.title("Cost of generating the provenance report")
    save_figure("figure_S2B_provenance_overhead")

    # Supplementary Figure S2C: run-order drift
    plt.figure(figsize=(7.2, 5.2))
    plt.scatter(
        measured["run_order"],
        measured["runtime_ratio_to_case_median"],
        s=18,
    )
    plt.axhline(1.0, linestyle="--")
    plt.xlabel("Randomized measured-run order")
    plt.ylabel("Elapsed time / configuration median")
    plt.title("No material runtime drift across the formal benchmark")
    save_figure("figure_S2C_run_order_qc")

    print("PASS — Experiment 2 source record validated and analysis reproduced.")
    print(f"Derived tables: {DERIVED}")
    print(f"Manuscript table: {TABLES / 'experiment2_key_results.tsv'}")
    print(f"Figures: {FIGURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

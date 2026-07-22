#!/usr/bin/env python3
"""Reproduce NEXCISION Experiment 2 derived tables and manuscript figures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments" / "experiment_2_scalability"
FORMAL = EXP / "results" / "formal"
DERIVED = FORMAL / "derived"
FIGURES = ROOT / "manuscript" / "figures" / "experiment_2"


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


def main() -> int:
    args = parse_args()
    measured, summary, system_start, system_end = load_inputs(args.job_id)

    if len(measured) != 105:
        raise SystemExit(f"Expected 105 measured runs; observed {len(measured)}.")
    if not measured["correct"].astype(bool).all():
        raise SystemExit("At least one measured run failed correctness checks.")
    if len(summary) != 21:
        raise SystemExit(f"Expected 21 configurations; observed {len(summary)}.")
    if not summary["all_correct"].astype(bool).all():
        raise SystemExit("At least one summary configuration is not fully correct.")
    if not summary["deterministic_output"].astype(bool).all():
        raise SystemExit("At least one configuration has non-deterministic output.")

    DERIVED.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

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

    print("PASS — Experiment 2 analysis reproduced successfully.")
    print(f"Derived tables: {DERIVED}")
    print(f"Figures: {FIGURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

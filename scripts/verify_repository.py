#!/usr/bin/env python3
"""Dependency-free integrity audit for the NEXCISION benchmarking repository."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WHEEL_SHA256 = "f980aa7e1f4b5ef67ebe10b4117a07af3405ee0cd3805c1d2d9e936a284689d4"


class AuditFailure(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise AuditFailure("Cannot summarize an empty measurement list.")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def close_enough(observed: object, expected: float) -> bool:
    return math.isclose(
        float(observed), float(expected), rel_tol=1e-12, abs_tol=1e-9
    )


def check_required_files() -> None:
    required = [
        ".gitignore",
        "CITATION.cff",
        "LICENSE",
        "README.md",
        "software/nexcision-0.1.0-py3-none-any.whl",
        "software/SHA256SUMS.txt",
        "environments/experiment1-requirements.txt",
        "environments/experiment2-analysis-requirements.txt",
        "experiments/experiment_1_correctness/validation/experiment1_summary.json",
        "experiments/experiment_2_scalability/configs/formal_manifest.tsv",
        "experiments/experiment_2_scalability/results/formal/formal_measured-2432330.tsv",
        "experiments/experiment_2_scalability/results/formal/formal_summary-2432330.tsv",
        "experiments/experiment_2_scalability/results/formal/system_info-start-2432330.json",
        "experiments/experiment_2_scalability/results/formal/system_info-end-2432330.json",
        "experiments/experiment_2_scalability/results/formal/SOURCE_SHA256SUMS.txt",
        "experiments/experiment_2_scalability/analysis/analyse_formal_results.py",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise AuditFailure("Missing required files:\n" + "\n".join(missing))


def check_unwanted_artifacts() -> None:
    forbidden_names = {".DS_Store", "Thumbs.db"}
    forbidden_suffixes = {".pyc", ".pyo", ".zip", ".tar", ".gz", ".tmp", ".bak"}
    forbidden_parts = {
        "__pycache__",
        ".pytest_cache",
        ".hypothesis",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
    }
    generated_corpus = (
        ROOT
        / "experiments"
        / "experiment_1_correctness"
        / "validation"
        / "synthetic"
        / "cases_1000"
    )
    problems: list[str] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in forbidden_parts or part.startswith(".venv-") for part in relative.parts):
            problems.append(str(relative))
        if path.is_file() and (
            path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes
        ):
            problems.append(str(relative))
    if generated_corpus.exists():
        problems.append(str(generated_corpus.relative_to(ROOT)))
    if problems:
        raise AuditFailure(
            "Generated or unwanted repository artefacts detected:\n"
            + "\n".join(sorted(set(problems)))
        )


def check_python_syntax() -> None:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as error:
            failures.append(f"{path.relative_to(ROOT)}: {error}")
    if failures:
        raise AuditFailure("Python syntax failures:\n" + "\n".join(failures))


def check_markdown_links() -> None:
    markdown_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    image_pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    html_pattern = re.compile(r'(?:href|src)="([^"]+)"')
    broken: list[str] = []

    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        targets = (
            [match.group(1) for match in markdown_pattern.finditer(text)]
            + [match.group(1) for match in image_pattern.finditer(text)]
            + [match.group(1) for match in html_pattern.finditer(text)]
        )
        for target in targets:
            target = target.strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split()[0]
            local = unquote(target.split("#", 1)[0])
            if not local:
                continue
            resolved = (path.parent / local).resolve()
            if not resolved.exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    if broken:
        raise AuditFailure("Broken relative Markdown links:\n" + "\n".join(broken))


def check_wheel() -> None:
    wheel = ROOT / "software" / "nexcision-0.1.0-py3-none-any.whl"
    observed = sha256_file(wheel)
    if observed != EXPECTED_WHEEL_SHA256:
        raise AuditFailure(
            f"Frozen wheel checksum mismatch: {observed} != {EXPECTED_WHEEL_SHA256}"
        )

    checksum_file = ROOT / "software" / "SHA256SUMS.txt"
    fields = checksum_file.read_text(encoding="utf-8").strip().split()
    if len(fields) != 2 or fields[0] != EXPECTED_WHEEL_SHA256:
        raise AuditFailure("software/SHA256SUMS.txt is invalid.")
    if fields[1] != wheel.name:
        raise AuditFailure("software/SHA256SUMS.txt names the wrong wheel.")



def check_experiment1_artifact_provenance() -> None:
    synthetic = (
        ROOT
        / "experiments"
        / "experiment_1_correctness"
        / "validation"
        / "synthetic"
    )

    wheel_name = "nexcision-0.1.0-py3-none-any.whl"
    historical_sha256 = (
        "e54ed4058f3736a5bc39a79d63dac4e2"
        "b43ba62a4a2f3631acc3d749b2ed0ceb"
    )
    revalidated_commit = (
        "5fff3aa03e581ff8644219e75c086ed140522b97"
    )

    record_path = synthetic / "archival_revalidation_20260815.json"
    if not record_path.is_file():
        raise AuditFailure(
            "Experiment 1 archival revalidation record is missing."
        )

    record = json.loads(record_path.read_text(encoding="utf-8"))

    if record.get("schema_version") != 1:
        raise AuditFailure(
            "Experiment 1 archival revalidation has the wrong schema version."
        )

    if record.get("record_type") != "archival_revalidation":
        raise AuditFailure(
            "Experiment 1 archival revalidation has the wrong record type."
        )

    if record.get("repository_commit_revalidated") != revalidated_commit:
        raise AuditFailure(
            "Experiment 1 archival revalidation identifies the wrong "
            "repository commit."
        )

    artifact = record.get("frozen_artifact", {})
    if artifact.get("path") != f"software/{wheel_name}":
        raise AuditFailure(
            "Experiment 1 archival revalidation names the wrong frozen artifact."
        )
    if artifact.get("version") != "0.1.0":
        raise AuditFailure(
            "Experiment 1 archival revalidation records the wrong "
            "NEXCISION version."
        )
    if artifact.get("sha256") != EXPECTED_WHEEL_SHA256:
        raise AuditFailure(
            "Experiment 1 archival revalidation checksum does not match "
            "the frozen repository wheel."
        )

    expected_runs = {
        "synthetic_100_case_revalidation": {
            "cases": 100,
            "cases_passed": 100,
            "total_site_rows": 14800,
            "rows_removed": 5600,
            "rows_retained": 9200,
        },
        "synthetic_1000_case_revalidation": {
            "cases": 1000,
            "cases_passed": 1000,
            "total_site_rows": 304000,
            "rows_removed": 113740,
            "rows_retained": 190260,
        },
    }

    for key, expected in expected_runs.items():
        run = record.get(key, {})
        if run.get("status") != "PASS":
            raise AuditFailure(
                f"Experiment 1 archival revalidation does not PASS for {key}."
            )
        if run.get("oracle_agreement") is not True:
            raise AuditFailure(
                f"Experiment 1 archival revalidation lacks exact oracle "
                f"agreement for {key}."
            )

        for field, value in expected.items():
            if run.get(field) != value:
                raise AuditFailure(
                    f"Experiment 1 archival revalidation has unexpected "
                    f"{field} for {key}."
                )

        comparison = run.get("stored_result_comparison", {})
        if comparison.get("all_nonruntime_fields_identical") is not True:
            raise AuditFailure(
                f"Experiment 1 archival revalidation has substantive "
                f"result differences for {key}."
            )
        if comparison.get("differing_fields") != ["runtime_seconds"]:
            raise AuditFailure(
                f"Experiment 1 archival revalidation has unexpected "
                f"differing fields for {key}."
            )
        if comparison.get("ignored_nondeterministic_fields") != [
            "runtime_seconds"
        ]:
            raise AuditFailure(
                f"Experiment 1 archival revalidation has unexpected "
                f"nondeterministic fields for {key}."
            )

    corpus = record.get("regenerated_1000_case_corpus", {})
    if corpus.get("identical") is not True:
        raise AuditFailure(
            "Experiment 1 regenerated 1,000-case corpus is not identical."
        )

    corpus_record = (
        synthetic / "case_1000_corpus_sha256.txt"
    ).read_text(encoding="utf-8").split()[0]

    if (
        corpus.get("stored_sha256") != corpus_record
        or corpus.get("fresh_sha256") != corpus_record
    ):
        raise AuditFailure(
            "Experiment 1 archival revalidation corpus checksum does not "
            "match the repository record."
        )

    provenance = record.get("historical_provenance", {})
    if (
        provenance.get(
            "checksum_recorded_in_original_july_2026_synthetic_records"
        )
        != historical_sha256
    ):
        raise AuditFailure(
            "Experiment 1 archival revalidation does not preserve the "
            "historical July 2026 checksum."
        )

    if (
        provenance.get("checksum_of_wheel_frozen_in_repository")
        != EXPECTED_WHEEL_SHA256
    ):
        raise AuditFailure(
            "Experiment 1 archival revalidation records the wrong frozen "
            "repository checksum."
        )

    # Preserve the original July 2026 records exactly as historical evidence.
    historical_summary = json.loads(
        (synthetic / "case_100_summary.json").read_text(encoding="utf-8")
    )
    if historical_summary.get("tested_artifact") != wheel_name:
        raise AuditFailure(
            "Historical Experiment 1 summary names the wrong wheel."
        )
    if historical_summary.get("tested_artifact_sha256") != historical_sha256:
        raise AuditFailure(
            "Historical Experiment 1 checksum has been altered."
        )

    for name in ("case_100_report.md", "case_1000_report.md"):
        report = (synthetic / name).read_text(encoding="utf-8")
        if historical_sha256 not in report:
            raise AuditFailure(
                f"Historical checksum is missing from {name}."
            )

def check_experiment1_record() -> None:
    validation = (
        ROOT / "experiments" / "experiment_1_correctness" / "validation"
    )
    summary = json.loads((validation / "experiment1_summary.json").read_text())
    if summary.get("status") != "PASS" or not summary.get("acceptance_criteria_met"):
        raise AuditFailure("Experiment 1 summary is not a passing record.")

    expected = summary["key_result_checksums"]
    files = {
        "malformed_input_results_tsv": validation / "malformed_input_results.tsv",
        "mutation_results_tsv": validation / "mutation" / "mutation_results.tsv",
        "property_results_tsv": validation / "property" / "property_results.tsv",
        "real_file_sanity_checks_tsv": validation / "real_file_sanity_checks.tsv",
        "synthetic_1000_results_tsv": (
            validation / "synthetic" / "case_1000_results.tsv"
        ),
    }
    for label, path in files.items():
        observed = sha256_file(path)
        if observed != expected[label]:
            raise AuditFailure(
                f"Experiment 1 checksum mismatch for {path.relative_to(ROOT)}."
            )

    corpus = summary["synthetic_corpus"]
    if (
        corpus["cases"] != 1000
        or corpus["passed"] != 1000
        or corpus["total_site_rows"] != 304000
        or corpus["rows_removed"] != 113740
        or corpus["rows_retained"] != 190260
    ):
        raise AuditFailure("Experiment 1 synthetic-corpus totals are inconsistent.")


def check_checksum_manifest(directory: Path, manifest_name: str) -> None:
    manifest = directory / manifest_name
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(maxsplit=1)
        name = name.strip()
        path = directory / name
        if not path.is_file():
            raise AuditFailure(f"Checksum manifest names missing file: {path}")
        if sha256_file(path) != digest:
            raise AuditFailure(f"Checksum mismatch for {path.relative_to(ROOT)}.")


def check_experiment2_record() -> None:
    formal = (
        ROOT
        / "experiments"
        / "experiment_2_scalability"
        / "results"
        / "formal"
    )
    check_checksum_manifest(formal, "SOURCE_SHA256SUMS.txt")

    measured_path = formal / "formal_measured-2432330.tsv"
    summary_path = formal / "formal_summary-2432330.tsv"
    with measured_path.open(newline="", encoding="utf-8") as handle:
        measured = list(csv.DictReader(handle, delimiter="\t"))
    with summary_path.open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle, delimiter="\t"))

    if len(measured) != 105:
        raise AuditFailure(f"Expected 105 formal measurements; found {len(measured)}.")
    if len(summary) != 21:
        raise AuditFailure(f"Expected 21 formal summaries; found {len(summary)}.")
    if not all(int(row["returncode"]) == 0 and truthy(row["correct"]) for row in measured):
        raise AuditFailure("At least one formal measured execution is not correct.")
    if not all(
        truthy(row["all_correct"]) and truthy(row["deterministic_output"])
        for row in summary
    ):
        raise AuditFailure("At least one formal configuration is not fully passing.")

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in measured:
        groups[row["case_id"]].append(row)
    if len(groups) != 21:
        raise AuditFailure(f"Expected 21 measured case IDs; found {len(groups)}.")

    summary_by_case = {row["case_id"]: row for row in summary}
    if len(summary_by_case) != 21:
        raise AuditFailure("Formal summary case IDs are not unique.")

    for case_id, rows in groups.items():
        if len(rows) != 5:
            raise AuditFailure(f"{case_id} has {len(rows)} runs instead of five.")
        if sorted(int(row["repeat"]) for row in rows) != [1, 2, 3, 4, 5]:
            raise AuditFailure(f"{case_id} has unexpected repetition identifiers.")
        if len({row["filtered_sha256"] for row in rows}) != 1:
            raise AuditFailure(f"{case_id} has non-deterministic output.")
        for row in rows:
            if int(row["observed_retained_rows"]) != int(row["expected_retained_rows"]):
                raise AuditFailure(f"{case_id} has an incorrect retained-row count.")
            if int(row["observed_nchar"]) != int(row["expected_retained_rows"]):
                raise AuditFailure(f"{case_id} has an incorrect nchar.")
            if int(row["observed_ntax"]) != int(row["taxa"]):
                raise AuditFailure(f"{case_id} has an incorrect ntax.")

        stored = summary_by_case.get(case_id)
        if stored is None:
            raise AuditFailure(f"Summary is missing {case_id}.")
        elapsed = [float(row["elapsed_seconds"]) for row in rows]
        peak = [float(row["peak_rss_bytes"]) for row in rows]
        throughput = [float(row["throughput_input_mib_s"]) for row in rows]
        cpu_seconds = [float(row["cpu_seconds"]) for row in rows]
        cpu_efficiency = [float(row["cpu_efficiency"]) for row in rows]
        expected = {
            "n_runs": 5.0,
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
        expected["elapsed_iqr_seconds"] = (
            expected["elapsed_q3_seconds"] - expected["elapsed_q1_seconds"]
        )
        expected["peak_rss_median_gib"] = expected["peak_rss_median_bytes"] / (
            1024**3
        )
        for column, value in expected.items():
            if not close_enough(stored[column], value):
                raise AuditFailure(
                    f"Summary mismatch for {case_id}.{column}: "
                    f"{stored[column]} != {value}"
                )

    start = json.loads((formal / "system_info-start-2432330.json").read_text())
    end = json.loads((formal / "system_info-end-2432330.json").read_text())
    for label, snapshot in [("start", start), ("end", end)]:
        if str(snapshot["environment"]["SLURM_JOB_ID"]) != "2432330":
            raise AuditFailure(f"{label} snapshot records the wrong Slurm job.")
        if snapshot["software_wheel"]["sha256"] != EXPECTED_WHEEL_SHA256:
            raise AuditFailure(f"{label} snapshot records the wrong wheel.")
        if snapshot["commands"]["nexcise_version"]["stdout"] != "NEXCISION 0.1.0":
            raise AuditFailure(f"{label} snapshot records the wrong version.")
    if start["commands"]["hostname"]["stdout"] != end["commands"]["hostname"]["stdout"]:
        raise AuditFailure("Start and end snapshots record different hosts.")
    if start["commands"]["git_commit"]["stdout"] != end["commands"]["git_commit"]["stdout"]:
        raise AuditFailure("Start and end snapshots record different commits.")


def main() -> int:
    checks = [
        ("required files", check_required_files),
        ("repository hygiene", check_unwanted_artifacts),
        ("Python syntax", check_python_syntax),
        ("relative Markdown links", check_markdown_links),
        ("frozen wheel", check_wheel),
        ("Experiment 1 artifact provenance", check_experiment1_artifact_provenance),
        ("Experiment 1 record", check_experiment1_record),
        ("Experiment 2 record", check_experiment2_record),
    ]
    try:
        for label, function in checks:
            function()
            print(f"PASS — {label}")
    except AuditFailure as error:
        print(f"FAIL — {error}", file=sys.stderr)
        return 1

    print("PASS — repository integrity audit completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

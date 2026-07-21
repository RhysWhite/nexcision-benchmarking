#!/usr/bin/env python3
"""Run and measure one NEXCISION benchmark invocation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_matrix_rows(path: Path) -> tuple[int, int | None, int | None]:
    rows = 0
    ntax = None
    nchar = None
    in_matrix = False
    import re

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            lowered = line.strip().lower()
            if "dimensions" in lowered:
                ntax_match = re.search(r"\bntax\s*=\s*(\d+)", lowered)
                nchar_match = re.search(r"\bnchar\s*=\s*(\d+)", lowered)
                if ntax_match:
                    ntax = int(ntax_match.group(1))
                if nchar_match:
                    nchar = int(nchar_match.group(1))
            if lowered == "matrix":
                in_matrix = True
                continue
            if in_matrix:
                before, separator, _ = line.partition(";")
                if before.strip() and not before.lstrip().startswith("["):
                    rows += 1
                if separator:
                    break
    return rows, ntax, nchar


def max_rss_bytes(value: int) -> int:
    # Linux reports KiB; macOS reports bytes.
    if sys.platform == "darwin":
        return value
    return value * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--repeat", type=int, required=True)
    parser.add_argument("--with-report", action="store_true")
    parser.add_argument("--keep-output", action="store_true")
    args = parser.parse_args()

    case_dir = args.case_dir.resolve()
    metadata = json.loads((case_dir / "case.json").read_text())
    nexus = case_dir / "input.nex"
    regions = case_dir / "regions.tsv"

    output_root = Path(tempfile.mkdtemp(prefix=f"nexcision-{metadata['case_id']}-"))
    filtered = output_root / "filtered.nex"
    counts = output_root / "counts.tsv"
    report = output_root / "report.json"

    command = [
        sys.executable,
        "-m",
        "nexcision",
        str(nexus),
        str(regions),
        "--output",
        str(filtered),
        "--counts",
        str(counts),
    ]
    if args.with_report:
        command.extend(["--report", str(report)])

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    elapsed = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)

    observed_rows = None
    observed_ntax = None
    observed_nchar = None
    correctness = False
    output_bytes = 0
    output_sha256 = None

    if completed.returncode == 0 and filtered.exists():
        observed_rows, observed_ntax, observed_nchar = parse_matrix_rows(filtered)
        output_bytes = filtered.stat().st_size
        output_sha256 = sha256_file(filtered)
        correctness = (
            observed_rows == metadata["expected_retained_rows"]
            and observed_nchar == metadata["expected_retained_rows"]
            and observed_ntax == metadata["taxa"]
        )

    payload = {
        "case_id": metadata["case_id"],
        "repeat": args.repeat,
        "with_report": args.with_report,
        "command": command,
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "user_cpu_seconds": after.ru_utime - before.ru_utime,
        "system_cpu_seconds": after.ru_stime - before.ru_stime,
        "peak_rss_bytes": max_rss_bytes(after.ru_maxrss),
        "input_bytes": nexus.stat().st_size,
        "regions_bytes": regions.stat().st_size,
        "output_bytes": output_bytes,
        "throughput_input_mib_s": (nexus.stat().st_size / (1024**2)) / elapsed,
        "expected_removed_rows": metadata["expected_removed_rows"],
        "expected_retained_rows": metadata["expected_retained_rows"],
        "observed_retained_rows": observed_rows,
        "observed_ntax": observed_ntax,
        "observed_nchar": observed_nchar,
        "correct": correctness,
        "filtered_sha256": output_sha256,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }

    print(json.dumps(payload, sort_keys=True))

    if not args.keep_output:
        shutil.rmtree(output_root, ignore_errors=True)

    return 0 if correctness else 1


if __name__ == "__main__":
    raise SystemExit(main())

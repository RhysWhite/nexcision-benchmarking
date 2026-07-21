#!/usr/bin/env python3
"""Regenerate and validate the full 1,000-case Experiment 1 corpus."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "experiment_1_correctness"
SYN = EXP / "validation" / "synthetic"


def run(label: str, command: list[str]) -> None:
    print(f"\n=== {label} ===", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    run("lightweight validation stack", [sys.executable, str(ROOT / "scripts" / "run_experiment1_light.py")])
    run("generate 1,000 deterministic matrices", [sys.executable, str(SYN / "generate_1000_cases.py")])
    run(
        "validate 1,000-case corpus",
        [
            sys.executable,
            str(SYN / "run_1000_cases_fast.py"),
            "--results",
            str(SYN / "case_1000_results.tsv"),
            "--summary",
            str(SYN / "case_1000_summary.json"),
        ],
    )
    run(
        "hash generated corpus",
        [
            sys.executable,
            str(SYN / "hash_corpus.py"),
            str(SYN / "cases_1000"),
            "--output",
            str(SYN / "case_1000_corpus_sha256.txt"),
        ],
    )
    print("\nPASS — full Experiment 1 corpus regenerated and validated", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

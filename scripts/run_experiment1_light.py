#!/usr/bin/env python3
"""Run the lightweight reproducibility suite for NEXCISION Experiment 1."""
from __future__ import annotations

import hashlib
import importlib.metadata
import subprocess
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "experiment_1_correctness"
VAL = EXP / "validation"
WHEEL = ROOT / "software" / "nexcision-0.1.0-py3-none-any.whl"
EXPECTED_WHEEL_SHA256 = "f980aa7e1f4b5ef67ebe10b4117a07af3405ee0cd3805c1d2d9e936a284689d4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(label: str, command: list[str]) -> None:
    print(f"\n=== {label} ===", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    if not WHEEL.is_file():
        print(f"ERROR: tested wheel is missing: {WHEEL}", file=sys.stderr)
        return 2
    observed = sha256(WHEEL)
    if observed != EXPECTED_WHEEL_SHA256:
        print("ERROR: tested wheel checksum does not match the Experiment 1 record.", file=sys.stderr)
        print(f"Expected: {EXPECTED_WHEEL_SHA256}", file=sys.stderr)
        print(f"Observed: {observed}", file=sys.stderr)
        return 2

    try:
        version = importlib.metadata.version("nexcision")
    except importlib.metadata.PackageNotFoundError:
        print(
            "ERROR: NEXCISION is not installed. Run:\n"
            "  python -m pip install software/nexcision-0.1.0-py3-none-any.whl",
            file=sys.stderr,
        )
        return 2
    if version != "0.1.0":
        print(f"ERROR: installed NEXCISION version is {version}; expected 0.1.0.", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="nexcision-experiment1-light-") as temporary:
        temporary_root = Path(temporary)
        commands = [
            (
                "software unit tests",
                [sys.executable, "-m", "unittest", "discover", "-s", str(EXP / "software_tests"), "-v"],
            ),
            ("fixed correctness cases", [sys.executable, str(VAL / "run_fixed_cases.py")]),
            ("all-sites safety case", [sys.executable, str(VAL / "run_safety_cases.py")]),
            ("malformed-input safety cases", [sys.executable, str(VAL / "run_invalid_cases.py")]),
            ("synthetic pilot", [sys.executable, str(VAL / "synthetic" / "run_pilot_cases.py")]),
            (
                "property-based validation",
                [sys.executable, str(VAL / "property" / "run_property_tests.py"), "--output-dir", str(temporary_root / "property")],
            ),
            (
                "mutation testing",
                [sys.executable, str(VAL / "mutation" / "run_mutation_panel.py"), "--output-dir", str(temporary_root / "mutation")],
            ),
        ]
        for label, command in commands:
            run(label, command)

    print("\nPASS — Experiment 1 lightweight reproducibility suite", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

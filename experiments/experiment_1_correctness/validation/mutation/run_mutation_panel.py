#!/usr/bin/env python3
"""Create deliberate source mutants and verify that validation kills them."""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import nexcision

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLED_PACKAGE = Path(nexcision.__file__).resolve().parent
INSTALLED_PARENT = INSTALLED_PACKAGE.parent
CORE = INSTALLED_PACKAGE / "core.py"
PROBE = Path(__file__).resolve().parent / "mutation_probe.py"
HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Mutation:
    mutation_id: str
    description: str
    old: str
    new: str


MUTATIONS = [
    Mutation(
        "M01_START_EXCLUSIVE",
        "Treat an interval start coordinate as outside the interval.",
        "index = bisect.bisect_right(starts, position) - 1",
        "index = bisect.bisect_left(starts, position) - 1",
    ),
    Mutation(
        "M02_END_EXCLUSIVE",
        "Treat an interval end coordinate as outside the interval.",
        "return index >= 0 and position <= intervals[index][1]",
        "return index >= 0 and position < intervals[index][1]",
    ),
    Mutation(
        "M03_UPDATE_NTAX",
        "Update ntax rather than nchar for a transposed matrix.",
        'return "nchar" if _matrix_is_transposed(prefix) else "ntax"',
        'return "ntax"',
    ),
    Mutation(
        "M04_DO_NOT_SORT_REGIONS",
        "Process regions in submitted order without sorting them.",
        "intervals = sorted((region.start, region.end) for region in regions)",
        "intervals = [(region.start, region.end) for region in regions]",
    ),
    Mutation(
        "M05_DISCARD_OVERLAP_EXTENSION",
        "Fail to extend a merged interval to the later overlapping endpoint.",
        "merged[-1] = (previous_start, max(previous_end, end))",
        "merged[-1] = (previous_start, previous_end)",
    ),
    Mutation(
        "M06_ONLY_FIRST_REGION",
        "Ignore every exclusion interval except the first after sorting.",
        "intervals = sorted((region.start, region.end) for region in regions)",
        "intervals = sorted((region.start, region.end) for region in regions)[:1]",
    ),
    Mutation(
        "M07_FIRST_INTEGER_IN_LABEL",
        "Extract the first integer in a row label instead of the requested terminal coordinate.",
        "match = pattern.search(token)",
        'match = re.search(r"(\\d+)", token)',
    ),
    Mutation(
        "M08_REVERSE_RETAINED_ROWS",
        "Insert retained rows at the start of the matrix and reverse their order.",
        "        else:\n            parsed_rows_kept += 1\n            output_lines.append(line)\n",
        "        else:\n            parsed_rows_kept += 1\n            output_lines.insert(matrix_start + 1, line)\n",
    ),
    Mutation(
        "M09_DROP_INLINE_TERMINATOR",
        "Remove the final inline row without restoring the MATRIX semicolon.",
        'output_lines.append(f";{after.rstrip(chr(10))}{newline}")',
        'output_lines.append(f"{after.rstrip(chr(10))}{newline}")',
    ),
    Mutation(
        "M10_DISABLE_EMPTY_SAFETY",
        "Allow all matrix rows to be removed without --allow-empty.",
        "if rows_kept == 0 and not allow_empty:",
        "if False and rows_kept == 0 and not allow_empty:",
    ),
    Mutation(
        "M11_DEDUPLICATE_REMOVED_COORDINATES",
        "Count duplicate-coordinate rows only once in regional counts.",
        "positions = sorted(removed_positions)",
        "positions = sorted(set(removed_positions))",
    ),
    Mutation(
        "M12_TOTAL_COUNT_FOR_EVERY_REGION",
        "Report the total number removed for every individual region.",
        "        left = bisect.bisect_left(positions, region.start)\n        right = bisect.bisect_right(positions, region.end)\n",
        "        left = 0\n        right = len(positions)\n",
    ),
]


def run_probe(source_root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(PROBE)],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    original = CORE.read_text(encoding="utf-8")
    baseline = run_probe(INSTALLED_PARENT)
    if baseline.returncode != 0:
        print("FAIL — unmodified NEXCISION did not pass the mutation probe", file=sys.stderr)
        print(baseline.stdout, file=sys.stderr)
        print(baseline.stderr, file=sys.stderr)
        return 1

    started = time.perf_counter()
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="nexcision-mutation-") as directory:
        root = Path(directory)
        for mutation in MUTATIONS:
            occurrences = original.count(mutation.old)
            if occurrences != 1:
                print(
                    f"FAIL — {mutation.mutation_id}: expected one mutation target, found {occurrences}",
                    file=sys.stderr,
                )
                return 1

            mutant_root = root / mutation.mutation_id / "src"
            shutil.copytree(INSTALLED_PACKAGE, mutant_root / "nexcision")
            mutant_core = mutant_root / "nexcision" / "core.py"
            mutant_core.write_text(original.replace(mutation.old, mutation.new, 1), encoding="utf-8")

            completed = run_probe(mutant_root)
            killed = completed.returncode != 0
            failure_line = ""
            combined = (completed.stderr + "\n" + completed.stdout).strip().splitlines()
            if combined:
                failure_line = combined[-1][:500]
            rows.append(
                {
                    "mutation_id": mutation.mutation_id,
                    "description": mutation.description,
                    "status": "KILLED" if killed else "SURVIVED",
                    "probe_exit_code": completed.returncode,
                    "detected_by": failure_line,
                }
            )
            print(f"{'KILLED' if killed else 'SURVIVED'} — {mutation.mutation_id}")

    with (output_dir / "mutation_results.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["mutation_id", "description", "status", "probe_exit_code", "detected_by"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    killed_count = sum(row["status"] == "KILLED" for row in rows)
    summary = {
        "mutants": len(rows),
        "mutants_killed": killed_count,
        "mutants_survived": len(rows) - killed_count,
        "mutation_score_percent": 100.0 * killed_count / len(rows),
        "baseline_probe_passed": True,
        "wall_seconds": time.perf_counter() - started,
    }
    (output_dir / "mutation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if killed_count != len(rows):
        print(f"FAIL — {len(rows) - killed_count} mutants survived", file=sys.stderr)
        return 1
    print(f"PASS — all {killed_count}/{len(rows)} deliberate mutants were detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

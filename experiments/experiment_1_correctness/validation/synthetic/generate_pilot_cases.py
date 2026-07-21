#!/usr/bin/env python3
"""Generate ten small, deterministic synthetic NEXUS validation cases.

The cases are intentionally small enough to inspect by eye. This generator does
not import NEXCISION. Expected row membership is calculated with a naive,
inclusive interval rule.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES_ROOT = ROOT / "pilot_cases"
MANIFEST = ROOT / "pilot_case_manifest.tsv"
SYMBOLS = "ACGT"


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    description: str
    ntax: int
    coordinates: tuple[int, ...]
    regions: tuple[tuple[int, int, str], ...]
    row_order: str
    interval_geometry: str
    separator: str = "tab"


CASES = (
    CaseSpec(
        "synthetic_001_basic_sorted",
        "Sorted rows with one ordinary interval removing two sites.",
        4,
        (100, 110, 120, 130, 140, 150, 160, 170),
        ((115, 135, "central_interval"),),
        "ascending",
        "single",
        "tab",
    ),
    CaseSpec(
        "synthetic_002_two_disjoint",
        "Two disjoint intervals remove one site each.",
        3,
        (10, 20, 30, 40, 50, 60, 70, 80, 90, 100),
        ((15, 25, "early"), (75, 85, "late")),
        "ascending",
        "disjoint",
        "space",
    ),
    CaseSpec(
        "synthetic_003_overlapping",
        "Overlapping intervals have independent counts but unique row removal.",
        5,
        (100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155),
        ((108, 128, "overlap_A"), (120, 142, "overlap_B")),
        "ascending",
        "overlapping",
        "tab",
    ),
    CaseSpec(
        "synthetic_004_shuffled_rows",
        "Matrix rows are deliberately shuffled and retained order must be preserved.",
        6,
        (300, 100, 250, 150, 200, 350, 125, 275, 175, 225, 325, 375),
        ((160, 260, "shuffled_target"),),
        "shuffled",
        "single",
        "space",
    ),
    CaseSpec(
        "synthetic_005_descending_rows",
        "Matrix coordinates descend rather than ascend.",
        2,
        (1000, 900, 800, 700, 600, 500, 400, 300, 200),
        ((450, 850, "descending_target"),),
        "descending",
        "single",
        "tab",
    ),
    CaseSpec(
        "synthetic_006_no_match",
        "A valid region contains no observed site coordinates.",
        10,
        (100, 110, 120, 130, 140, 150, 160, 170, 180, 190),
        ((1000, 1100, "no_match"),),
        "ascending",
        "no_match",
        "space",
    ),
    CaseSpec(
        "synthetic_007_reversed_interval",
        "A reversed interval is normalised before filtering.",
        7,
        (50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300),
        ((210, 90, "reversed"),),
        "ascending",
        "reversed",
        "tab",
    ),
    CaseSpec(
        "synthetic_008_duplicate_adjacent",
        "Duplicate and adjacent intervals are combined for membership but counted separately.",
        8,
        (100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230),
        ((115, 135, "duplicate_A"), (115, 135, "duplicate_B"), (136, 165, "adjacent")),
        "ascending",
        "duplicate_and_adjacent",
        "space",
    ),
    CaseSpec(
        "synthetic_009_half_removed",
        "Exactly half of the site rows are removed.",
        4,
        (100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250),
        ((100, 170, "first_half"),),
        "ascending",
        "single",
        "tab",
    ),
    CaseSpec(
        "synthetic_010_multiple_unsorted",
        "Four unsorted regions include three matching intervals and one no-match interval.",
        12,
        (100, 113, 126, 139, 152, 165, 178, 191, 204, 217, 230, 243, 256, 269, 282, 295, 308, 321),
        ((280, 315, "late"), (120, 155, "early"), (500, 550, "no_match"), (190, 245, "middle")),
        "ascending",
        "multiple_unsorted",
        "space",
    ),
)


def normalized_regions(spec: CaseSpec) -> list[tuple[int, int, str]]:
    return [(min(start, end), max(start, end), name) for start, end, name in spec.regions]


def should_remove(coordinate: int, spec: CaseSpec) -> bool:
    return any(start <= coordinate <= end for start, end, _ in normalized_regions(spec))


def state_string(case_id: str, coordinate: int, ntax: int, separator: str) -> str:
    states: list[str] = []
    for column in range(ntax):
        digest = hashlib.sha256(f"{case_id}:{coordinate}:{column}".encode()).digest()
        states.append(SYMBOLS[digest[0] % len(SYMBOLS)])
    joiner = "\t" if separator == "tab" else " "
    return joiner.join(states)


def make_nexus(spec: CaseSpec, coordinates: tuple[int, ...]) -> str:
    taxlabels = " ".join(f"sample_{index:03d}" for index in range(1, spec.ntax + 1))
    lines = [
        "#NEXUS\n",
        "begin data;\n",
        f"dimensions ntax={spec.ntax} nchar={len(coordinates)};\n",
        'format symbols="AGCT" gap=. transpose;\n',
        f"taxlabels {taxlabels};\n",
        "matrix\n",
    ]
    for coordinate in coordinates:
        states = state_string(spec.case_id, coordinate, spec.ntax, spec.separator)
        lines.append(f"SYNTHREF_1_{coordinate}\t{states}\n")
    lines.extend([";\n", "end;\n"])
    return "".join(lines)


def write_rows(path: Path, coordinates: list[int]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["row_label", "coordinate"])
        for coordinate in coordinates:
            writer.writerow([f"SYNTHREF_1_{coordinate}", coordinate])


def write_case(spec: CaseSpec) -> dict[str, object]:
    case_dir = CASES_ROOT / spec.case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    input_text = make_nexus(spec, spec.coordinates)
    removed = [coordinate for coordinate in spec.coordinates if should_remove(coordinate, spec)]
    retained = [coordinate for coordinate in spec.coordinates if not should_remove(coordinate, spec)]
    expected_text = make_nexus(spec, tuple(retained))

    (case_dir / "input.nex").write_text(input_text, encoding="utf-8")
    (case_dir / "expected_filtered.nex").write_text(expected_text, encoding="utf-8")

    with (case_dir / "regions.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["start", "end", "name"])
        for start, end, name in spec.regions:
            writer.writerow([start, end, name])

    write_rows(case_dir / "expected_removed.tsv", removed)
    write_rows(case_dir / "expected_retained.tsv", retained)

    normalized = normalized_regions(spec)
    with (case_dir / "expected_oracle_counts.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["region_id", "region_name", "start", "end", "expected_removed_rows"])
        for index, (start, end, name) in enumerate(normalized, start=1):
            count = sum(start <= coordinate <= end for coordinate in removed)
            writer.writerow([index, name, start, end, count])

    with (case_dir / "expected_nexcision_counts.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["region_id", "region_name", "start", "end", "removed_rows"])
        for index, (start, end, name) in enumerate(normalized, start=1):
            count = sum(start <= coordinate <= end for coordinate in removed)
            writer.writerow([index, name, start, end, count])

    summary = {
        "expected_rows_removed": len(removed),
        "expected_rows_retained": len(retained),
        "matrix_rows_read": len(spec.coordinates),
        "regions_loaded": len(spec.regions),
    }
    (case_dir / "expected_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    removal_fraction = len(removed) / len(spec.coordinates)
    (case_dir / "README.md").write_text(
        f"# {spec.case_id}\n\n"
        f"{spec.description}\n\n"
        f"- Taxa/sample columns: `{spec.ntax}`\n"
        f"- Site rows: `{len(spec.coordinates)}`\n"
        f"- Row order: `{spec.row_order}`\n"
        f"- Interval geometry: `{spec.interval_geometry}`\n"
        f"- Expected rows removed: `{len(removed)}`\n"
        f"- Expected rows retained: `{len(retained)}`\n"
        f"- Removal fraction: `{removal_fraction:.3f}`\n",
        encoding="utf-8",
    )

    return {
        "case_id": spec.case_id,
        "description": spec.description,
        "ntax": spec.ntax,
        "nchar": len(spec.coordinates),
        "interval_count": len(spec.regions),
        "row_order": spec.row_order,
        "interval_geometry": spec.interval_geometry,
        "separator": spec.separator,
        "expected_removed": len(removed),
        "expected_retained": len(retained),
        "removal_fraction": f"{removal_fraction:.3f}",
        "expected_removed_labels": ";".join(f"SYNTHREF_1_{coordinate}" for coordinate in removed) or "none",
    }


def main() -> int:
    if CASES_ROOT.exists():
        shutil.rmtree(CASES_ROOT)
    CASES_ROOT.mkdir(parents=True)

    rows = [write_case(spec) for spec in CASES]
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} deterministic synthetic pilot cases.")
    print(f"Cases: {CASES_ROOT}")
    print(f"Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

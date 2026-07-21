#!/usr/bin/env python3
"""Generate 1,000 deterministic synthetic NEXUS correctness cases.

The corpus contains ten scenario families with one hundred deterministic variants each. It does
not import NEXCISION. Expected row membership is calculated using a direct,
inclusive interval rule.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES_ROOT = ROOT / "cases_1000"
MANIFEST = ROOT / "case_1000_manifest.tsv"
SYMBOLS = "ACGT"
MASTER_SEED = 20260721

NTAX_VALUES = (
    2, 3, 4, 6, 8, 10, 12, 16, 20, 24,
    32, 40, 48, 64, 80, 96, 128, 160, 192, 256,
)
NCHAR_VALUES = (
    20, 30, 40, 50, 60, 80, 100, 120, 150, 180,
    200, 250, 300, 350, 400, 500, 600, 750, 900, 1000,
)


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    family: str
    description: str
    ntax: int
    coordinates: tuple[int, ...]
    regions: tuple[tuple[int, int, str], ...]
    row_order: str
    interval_geometry: str
    separator: str
    seed: int


def stable_int(text: str, modulus: int) -> int:
    digest = hashlib.sha256(text.encode()).digest()
    return int.from_bytes(digest[:8], "big") % modulus


def ordered_coordinates(nchar: int, seed: int) -> list[int]:
    """Create unique, irregular but increasing 1-based coordinates."""
    rng = random.Random(seed)
    current = 100 + rng.randint(0, 50)
    coords: list[int] = []
    for _ in range(nchar):
        current += rng.randint(3, 19)
        coords.append(current)
    return coords


def interval_from_indices(coords: list[int], left: int, right: int) -> tuple[int, int]:
    left = max(0, min(left, len(coords) - 1))
    right = max(0, min(right, len(coords) - 1))
    if left > right:
        left, right = right, left
    return coords[left], coords[right]


def make_regions(family: str, coords_sorted: list[int]) -> tuple[tuple[int, int, str], ...]:
    n = len(coords_sorted)
    q10 = max(0, n // 10)
    q20 = max(q10, n // 5)
    q30 = max(q20, (3 * n) // 10)
    q40 = max(q30, (2 * n) // 5)
    q50 = max(q40, n // 2)
    q60 = max(q50, (3 * n) // 5)
    q70 = max(q60, (7 * n) // 10)
    q80 = max(q70, (4 * n) // 5)
    q90 = max(q80, (9 * n) // 10)

    if family == "basic_single":
        a, b = interval_from_indices(coords_sorted, q30, q50)
        return ((a, b, "central"),)

    if family == "two_disjoint":
        a1, b1 = interval_from_indices(coords_sorted, q10, q20)
        a2, b2 = interval_from_indices(coords_sorted, q70, q80)
        return ((a1, b1, "early"), (a2, b2, "late"))

    if family == "overlapping":
        a1, b1 = interval_from_indices(coords_sorted, q20, q55(n))
        a2, b2 = interval_from_indices(coords_sorted, q40, q70)
        return ((a1, b1, "overlap_A"), (a2, b2, "overlap_B"))

    if family == "shuffled_rows":
        a, b = interval_from_indices(coords_sorted, q25(n), q60)
        return ((a, b, "shuffled_target"),)

    if family == "descending_rows":
        a, b = interval_from_indices(coords_sorted, q15(n), q65(n))
        return ((a, b, "descending_target"),)

    if family == "no_match":
        gap = max(100, coords_sorted[-1] - coords_sorted[0])
        return ((coords_sorted[-1] + gap, coords_sorted[-1] + gap + 100, "no_match"),)

    if family == "reversed_interval":
        a, b = interval_from_indices(coords_sorted, q25(n), q65(n))
        return ((b, a, "reversed"),)

    if family == "duplicate_adjacent":
        a1, b1 = interval_from_indices(coords_sorted, q15(n), q30)
        _, b2 = interval_from_indices(coords_sorted, q31(n), q50)
        a2 = b1 + 1
        return (
            (a1, b1, "duplicate_A"),
            (a1, b1, "duplicate_B"),
            (a2, b2, "adjacent"),
        )

    if family == "multiple_unsorted":
        late_a, late_b = interval_from_indices(coords_sorted, q75(n), q90)
        early_a, early_b = interval_from_indices(coords_sorted, q10, q25(n))
        middle_a, middle_b = interval_from_indices(coords_sorted, q45(n), q60)
        gap = max(100, coords_sorted[-1] - coords_sorted[0])
        return (
            (late_a, late_b, "late"),
            (early_a, early_b, "early"),
            (coords_sorted[-1] + gap, coords_sorted[-1] + gap + 100, "no_match"),
            (middle_a, middle_b, "middle"),
        )

    if family == "nested_threeway":
        outer_a, outer_b = interval_from_indices(coords_sorted, q15(n), q80)
        inner_a, inner_b = interval_from_indices(coords_sorted, q35(n), q55(n))
        partial_a, partial_b = interval_from_indices(coords_sorted, q60, q90)
        return (
            (outer_a, outer_b, "outer"),
            (inner_a, inner_b, "nested"),
            (partial_a, partial_b, "partial_overlap"),
        )

    raise ValueError(f"Unknown family: {family}")


def q15(n: int) -> int:
    return max(0, (15 * n) // 100)


def q25(n: int) -> int:
    return max(0, n // 4)


def q31(n: int) -> int:
    return max(0, (31 * n) // 100)


def q35(n: int) -> int:
    return max(0, (35 * n) // 100)


def q45(n: int) -> int:
    return max(0, (45 * n) // 100)


def q55(n: int) -> int:
    return max(0, (55 * n) // 100)


def q65(n: int) -> int:
    return max(0, (65 * n) // 100)


def q75(n: int) -> int:
    return max(0, (75 * n) // 100)


def build_specs() -> tuple[CaseSpec, ...]:
    families = (
        ("basic_single", "One ordinary interval."),
        ("two_disjoint", "Two disjoint intervals."),
        ("overlapping", "Two overlapping intervals with independent counts."),
        ("shuffled_rows", "Shuffled matrix rows with retained-order preservation."),
        ("descending_rows", "Coordinates in descending matrix order."),
        ("no_match", "A valid interval with no observed sites."),
        ("reversed_interval", "A reversed interval normalised before filtering."),
        ("duplicate_adjacent", "Duplicate plus adjacent or nearby intervals."),
        ("multiple_unsorted", "Multiple intervals supplied out of genomic order."),
        ("nested_threeway", "Nested and partially overlapping intervals."),
    )

    specs: list[CaseSpec] = []
    case_number = 1
    for family_index, (family, description) in enumerate(families):
        for size_index in range(1, 101):
            # Cycle through a broad set of matrix shapes while changing the
            # coordinate and state content for every deterministic variant.
            ntax = NTAX_VALUES[(size_index - 1 + family_index * 3) % len(NTAX_VALUES)]
            nchar = NCHAR_VALUES[((size_index - 1) * 7 + family_index * 5) % len(NCHAR_VALUES)]
            seed = MASTER_SEED + family_index * 100_000 + size_index
            sorted_coords = ordered_coordinates(nchar, seed)
            row_order = "ascending"
            coords = list(sorted_coords)
            if family == "shuffled_rows":
                random.Random(seed + 500_000).shuffle(coords)
                row_order = "shuffled"
            elif family == "descending_rows":
                coords.reverse()
                row_order = "descending"

            regions = make_regions(family, sorted_coords)
            case_id = f"synthetic_{case_number:04d}_{family}_{size_index:03d}"
            specs.append(
                CaseSpec(
                    case_id=case_id,
                    family=family,
                    description=description,
                    ntax=ntax,
                    coordinates=tuple(coords),
                    regions=regions,
                    row_order=row_order,
                    interval_geometry=family,
                    separator="tab" if case_number % 2 else "space",
                    seed=seed,
                )
            )
            case_number += 1
    return tuple(specs)


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
    if not retained:
        raise ValueError(f"Synthetic correctness case would remove all rows: {spec.case_id}")
    expected_text = make_nexus(spec, tuple(retained))

    (case_dir / "input.nex").write_text(input_text, encoding="utf-8")
    (case_dir / "expected_filtered.nex").write_text(expected_text, encoding="utf-8")

    with (case_dir / "regions.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["start", "end", "name"])
        writer.writerows(spec.regions)

    write_rows(case_dir / "expected_removed.tsv", removed)
    write_rows(case_dir / "expected_retained.tsv", retained)

    normalized = normalized_regions(spec)
    oracle_count_rows: list[list[object]] = []
    tool_count_rows: list[list[object]] = []
    for index, (start, end, name) in enumerate(normalized, start=1):
        count = sum(start <= coordinate <= end for coordinate in removed)
        oracle_count_rows.append([index, name, start, end, count])
        tool_count_rows.append([index, name, start, end, count])

    with (case_dir / "expected_oracle_counts.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["region_id", "region_name", "start", "end", "expected_removed_rows"])
        writer.writerows(oracle_count_rows)

    with (case_dir / "expected_nexcision_counts.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["region_id", "region_name", "start", "end", "removed_rows"])
        writer.writerows(tool_count_rows)

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
        f"- Family: `{spec.family}`\n"
        f"- Seed: `{spec.seed}`\n"
        f"- Taxa/sample columns: `{spec.ntax}`\n"
        f"- Site rows: `{len(spec.coordinates)}`\n"
        f"- Row order: `{spec.row_order}`\n"
        f"- Interval geometry: `{spec.interval_geometry}`\n"
        f"- Regions: `{len(spec.regions)}`\n"
        f"- Expected rows removed: `{len(removed)}`\n"
        f"- Expected rows retained: `{len(retained)}`\n"
        f"- Removal fraction: `{removal_fraction:.4f}`\n",
        encoding="utf-8",
    )

    return {
        "case_id": spec.case_id,
        "family": spec.family,
        "description": spec.description,
        "seed": spec.seed,
        "ntax": spec.ntax,
        "nchar": len(spec.coordinates),
        "interval_count": len(spec.regions),
        "row_order": spec.row_order,
        "interval_geometry": spec.interval_geometry,
        "separator": spec.separator,
        "expected_removed": len(removed),
        "expected_retained": len(retained),
        "removal_fraction": f"{removal_fraction:.4f}",
    }


def main() -> int:
    specs = build_specs()
    if len(specs) != 1000:
        raise RuntimeError(f"Expected 1,000 specifications, found {len(specs)}")

    if CASES_ROOT.exists():
        shutil.rmtree(CASES_ROOT)
    CASES_ROOT.mkdir(parents=True)

    rows = [write_case(spec) for spec in specs]
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} deterministic synthetic correctness cases.")
    print(f"Cases: {CASES_ROOT}")
    print(f"Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

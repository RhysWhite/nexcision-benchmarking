#!/usr/bin/env python3
"""Independent behavioural probe used to kill deliberate NEXCISION mutants."""
from __future__ import annotations

import csv
import re
import tempfile
from pathlib import Path

from nexcision import NexusFilterError, Region, filter_nexus_text, load_regions


def nexus(rows: list[tuple[str, str]], ntax: int = 3, *, inline: bool = False) -> str:
    lines = [
        "#NEXUS\n",
        "Begin data;\n",
        f"Dimensions ntax={ntax} nchar={len(rows)};\n",
        'Format datatype=standard symbols="01" gap=- transpose;\n',
        "Taxlabels A B C;\n",
        "Matrix\n",
    ]
    for index, (label, states) in enumerate(rows):
        terminator = ";" if inline and index == len(rows) - 1 else ""
        lines.append(f"    {label} {states}{terminator}\n")
    if not inline:
        lines.append(";\n")
    lines.append("End;\n")
    return "".join(lines)


def labels(text: str) -> list[str]:
    found: list[str] = []
    in_matrix = False
    terminated = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not in_matrix:
            if stripped.lower() == "matrix":
                in_matrix = True
            continue
        before, separator, _after = raw.partition(";")
        content = before.strip() if separator else stripped
        if content:
            parts = content.split(maxsplit=1)
            if len(parts) == 2:
                found.append(parts[0])
        if separator:
            terminated = True
            in_matrix = False
    assert terminated, "Filtered MATRIX is not terminated"
    return found


def dims(text: str) -> tuple[int, int]:
    match = re.search(r"ntax\s*=\s*(\d+).*?nchar\s*=\s*(\d+)", text, re.I | re.S)
    assert match
    return int(match.group(1)), int(match.group(2))


def count_rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(text.splitlines(), delimiter="\t"))


def run() -> None:
    # Inclusive start/end and retained order.
    text = nexus([
        ("REF_100", "0 0 0"),
        ("REF_110", "0 0 1"),
        ("REF_120", "0 1 1"),
        ("REF_130", "1 1 1"),
    ])
    filtered, _counts, result = filter_nexus_text(text, [Region(1, 110, 120, "bounds")])
    assert labels(filtered) == ["REF_100", "REF_130"]
    assert result.rows_removed == 2
    assert dims(filtered) == (3, 2)

    # Unsorted multiple regions, and no interval may be ignored.
    filtered, _counts, result = filter_nexus_text(
        text,
        [Region(1, 130, 130, "late"), Region(2, 100, 100, "early")],
    )
    assert labels(filtered) == ["REF_110", "REF_120"]
    assert result.rows_removed == 2

    # An overlapping region must extend the union to the later endpoint.
    overlap_text = nexus([("REF_120", "0 0 0"), ("REF_180", "1 0 1"), ("REF_220", "1 1 1")])
    filtered, _counts, _result = filter_nexus_text(
        overlap_text,
        [Region(1, 100, 150, "a"), Region(2, 140, 200, "b")],
    )
    assert labels(filtered) == ["REF_220"]

    # Per-region counts must remain region-specific.
    filtered, count_text, _result = filter_nexus_text(
        text,
        [Region(1, 100, 110, "first"), Region(2, 110, 130, "second")],
        allow_empty=True,
    )
    observed = count_rows(count_text)
    assert [int(row["removed_rows"]) for row in observed] == [2, 3]

    # Duplicate-coordinate rows count as two rows, not one coordinate.
    duplicate_text = nexus([
        ("first_100", "0 0 0"),
        ("second_100", "0 0 1"),
        ("third_200", "1 1 1"),
    ])
    filtered, count_text, result = filter_nexus_text(
        duplicate_text, [Region(1, 100, 100, "duplicate")]
    )
    assert labels(filtered) == ["third_200"]
    assert result.rows_removed == 2
    assert int(count_rows(count_text)[0]["removed_rows"]) == 2

    # The terminal coordinate—not an earlier number in the label—is used.
    digit_prefix = nexus([
        ("18AR0845_1_14268", "0 0 0"),
        ("18AR0845_1_15000", "1 1 1"),
    ])
    filtered, _counts, result = filter_nexus_text(
        digit_prefix, [Region(1, 14268, 14268, "target")]
    )
    assert labels(filtered) == ["18AR0845_1_15000"]
    assert result.rows_removed == 1

    # Custom regex must be honoured.
    custom = nexus([("sample18_pos500", "0 0 0"), ("sample18_pos600", "1 1 1")])
    filtered, _counts, result = filter_nexus_text(
        custom,
        [Region(1, 500, 500, "target")],
        position_pattern=r"_pos(\d+)$",
    )
    assert labels(filtered) == ["sample18_pos600"]
    assert result.rows_removed == 1

    # Removing an inline-terminated final row must leave a standalone terminator.
    inline = nexus([("REF_100", "0 0 0"), ("REF_200", "1 1 1")], inline=True)
    filtered, _counts, _result = filter_nexus_text(inline, [Region(1, 200, 200, "last")])
    assert labels(filtered) == ["REF_100"]
    assert re.search(r"\n\s*;\s*\nEnd;", filtered, re.I)

    # Empty-matrix protection must be active by default.
    try:
        filter_nexus_text(text, [Region(1, 1, 1_000, "all")])
    except NexusFilterError as exc:
        assert "remove all" in str(exc)
    else:
        raise AssertionError("All-sites safety was disabled")

    # Reversed region files must be normalised.
    with tempfile.TemporaryDirectory(prefix="nexcision-mutant-probe-") as directory:
        path = Path(directory) / "regions.tsv"
        path.write_text("start\tend\tname\n200\t100\treversed\n", encoding="utf-8")
        loaded = load_regions(path)
    assert (loaded[0].start, loaded[0].end) == (100, 200)

    # Multiple MATRIX blocks must be rejected.
    try:
        filter_nexus_text(text + text, [Region(1, 100, 100, "one")])
    except NexusFilterError as exc:
        assert "More than one MATRIX" in str(exc)
    else:
        raise AssertionError("Multiple MATRIX blocks were accepted")


if __name__ == "__main__":
    run()
    print("PASS — mutation probe")

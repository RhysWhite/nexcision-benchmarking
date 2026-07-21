#!/usr/bin/env python3
"""Preview exact synthetic NEXUS sizes without generating the files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def nexus_size_bytes(taxa: int, sites: int) -> int:
    total = len("#NEXUS\n\nbegin data;\n".encode())
    total += len(f"dimensions ntax={taxa} nchar={sites};\n".encode())
    total += len('format datatype=dna symbols="ACGT" gap=. transpose;\n'.encode())
    total += len("taxlabels\n".encode())
    total += sum(
        len(f"    sample_{taxon + 1:05d}\n".encode()) for taxon in range(taxa)
    )
    total += len(";\nmatrix\n".encode())
    sequence_bytes = taxa + max(0, taxa - 1)
    for row_index in range(sites):
        coordinate = 100 + row_index * 7
        total += len(f"REF_{coordinate}\t".encode()) + sequence_bytes + 1
    total += len(";\nend;\n".encode())
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    with args.manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    total = 0
    print("case_id\tseries\ttaxa\tsites\testimated_bytes\testimated_GiB")
    for row in rows:
        size = nexus_size_bytes(int(row["taxa"]), int(row["sites"]))
        total += size
        print(
            f"{row['case_id']}\t{row['series']}\t{row['taxa']}\t{row['sites']}\t"
            f"{size}\t{size / (1024**3):.6f}"
        )
    print(f"TOTAL\tall\t\t\t{total}\t{total / (1024**3):.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Load sample definitions from an optional samples.csv file."""

from __future__ import annotations

import csv
from pathlib import Path

from ecometa_flow.scanner import Sample, ScanError

REQUIRED_COLUMNS = ("SampleID", "R1", "R2")


def load_samples_csv(
    csv_path: Path, base_dir: Path | None = None
) -> list[Sample]:
    """
    Load samples from a CSV file.

    Required columns: SampleID, R1, R2
    Optional columns: Group, DataType, etc.
    """
    if not csv_path.is_file():
        raise ScanError(f"samples.csv not found: {csv_path}")

    base = base_dir or csv_path.parent
    samples: list[Sample] = []

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ScanError(f"samples.csv is empty or has no header: {csv_path}")

        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise ScanError(
                f"samples.csv is missing required columns: {', '.join(missing)}. "
                f"Required: {', '.join(REQUIRED_COLUMNS)}"
            )

        for row_num, row in enumerate(reader, start=2):
            sample_id = (row.get("SampleID") or "").strip()
            r1_raw = (row.get("R1") or "").strip()
            r2_raw = (row.get("R2") or "").strip()

            if not sample_id or not r1_raw or not r2_raw:
                raise ScanError(
                    f"samples.csv row {row_num}: SampleID, R1, and R2 are required."
                )

            r1 = Path(r1_raw)
            r2 = Path(r2_raw)
            if not r1.is_absolute():
                r1 = (base / r1).resolve()
            if not r2.is_absolute():
                r2 = (base / r2).resolve()

            if not r1.is_file():
                raise ScanError(f"samples.csv row {row_num}: R1 file not found: {r1}")
            if not r2.is_file():
                raise ScanError(f"samples.csv row {row_num}: R2 file not found: {r2}")

            samples.append(Sample(sample_id=sample_id, r1=r1, r2=r2))

    if not samples:
        raise ScanError(f"No samples found in {csv_path}")

    return samples

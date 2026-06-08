"""Scan input folders and detect paired-end FASTQ samples."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ecometa_flow.config import FASTQ_GLOBS

# Paired-end naming patterns supported in v0.1.0.
# Each tuple: (R1 regex, R2 regex, group index for sample name).
PAIR_PATTERNS: list[tuple[re.Pattern[str], re.Pattern[str], int]] = [
    (re.compile(r"^(.+)_R1(\.(?:fq|fastq)(?:\.gz)?)$"), re.compile(r"^(.+)_R2(\.(?:fq|fastq)(?:\.gz)?)$"), 1),
    (re.compile(r"^(.+)_1(\.(?:fq|fastq)(?:\.gz)?)$"), re.compile(r"^(.+)_2(\.(?:fq|fastq)(?:\.gz)?)$"), 1),
    (re.compile(r"^(.+)\.R1(\.(?:fq|fastq)(?:\.gz)?)$"), re.compile(r"^(.+)\.R2(\.(?:fq|fastq)(?:\.gz)?)$"), 1),
]


@dataclass
class Sample:
    """A paired-end sample with R1 and R2 file paths."""

    sample_id: str
    r1: Path
    r2: Path


class ScanError(Exception):
    """Raised when paired-end samples cannot be detected."""


def list_fastq_files(input_dir: Path) -> list[Path]:
    """Return all FASTQ files in a directory (non-recursive)."""
    if not input_dir.is_dir():
        raise ScanError(f"Input folder does not exist: {input_dir}")

    files: list[Path] = []
    for pattern in FASTQ_GLOBS:
        files.extend(sorted(input_dir.glob(pattern)))

    return files


def _match_read(filename: str, is_r1: bool) -> tuple[str, str] | None:
    """Try to match a filename against known R1/R2 patterns."""
    for r1_pat, r2_pat, group_idx in PAIR_PATTERNS:
        pattern = r1_pat if is_r1 else r2_pat
        match = pattern.match(filename)
        if match:
            sample_name = match.group(group_idx)
            suffix = match.group(2)
            return sample_name, suffix
    return None


def detect_paired_samples(input_dir: Path) -> list[Sample]:
    """
    Detect paired-end samples from FASTQ filenames.

    Supports Sample_R1.fq.gz, Sample_1.fq.gz, and Sample.R1.fq.gz patterns.
    """
    files = list_fastq_files(input_dir)
    if not files:
        raise ScanError(
            f"No FASTQ files found in {input_dir}. "
            "Expected *.fq.gz, *.fastq.gz, *.fq, or *.fastq files."
        )

    # Map (sample_name, suffix) -> {"r1": Path, "r2": Path}
    pairs: dict[tuple[str, str], dict[str, Path]] = {}

    for filepath in files:
        name = filepath.name
        r1_match = _match_read(name, is_r1=True)
        if r1_match:
            key = r1_match
            pairs.setdefault(key, {})["r1"] = filepath
            continue

        r2_match = _match_read(name, is_r1=False)
        if r2_match:
            key = r2_match
            pairs.setdefault(key, {})["r2"] = filepath
            continue

    samples: list[Sample] = []
    unmatched_r1: list[Path] = []
    unmatched_r2: list[Path] = []

    for (sample_name, _suffix), mates in sorted(pairs.items()):
        r1 = mates.get("r1")
        r2 = mates.get("r2")
        if r1 and r2:
            samples.append(Sample(sample_id=sample_name, r1=r1, r2=r2))
        elif r1:
            unmatched_r1.append(r1)
        elif r2:
            unmatched_r2.append(r2)

    if unmatched_r1 or unmatched_r2:
        orphan_files = unmatched_r1 + unmatched_r2
        orphan_names = ", ".join(f.name for f in orphan_files)
        raise ScanError(
            f"Found FASTQ files without a matching mate: {orphan_names}\n"
            "Please rename files to a supported pattern or use --samples samples.csv."
        )

    if not samples:
        raise ScanError(
            "Could not detect any paired-end samples from FASTQ filenames.\n"
            "Supported patterns:\n"
            "  Sample_R1.fq.gz / Sample_R2.fq.gz\n"
            "  Sample_1.fq.gz  / Sample_2.fq.gz\n"
            "  Sample.R1.fq.gz / Sample.R2.fq.gz\n"
            "If your files use different names, provide --samples samples.csv."
        )

    return samples

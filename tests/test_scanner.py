"""Tests for FASTQ scanning and paired-end detection."""

from pathlib import Path

import pytest

from ecometa_flow.scanner import ScanError, detect_paired_samples


@pytest.fixture
def reads_dir(tmp_path: Path) -> Path:
    """Create a temporary folder with paired FASTQ files."""
    folder = tmp_path / "raw_reads"
    folder.mkdir()
    for name in ("S1_R1.fq.gz", "S1_R2.fq.gz", "S2_R1.fq.gz", "S2_R2.fq.gz"):
        (folder / name).write_text("")
    return folder


def test_detect_r1_r2_pattern(reads_dir: Path) -> None:
    samples = detect_paired_samples(reads_dir)
    assert len(samples) == 2
    ids = {s.sample_id for s in samples}
    assert ids == {"S1", "S2"}


def test_detect_1_2_pattern(tmp_path: Path) -> None:
    folder = tmp_path / "reads"
    folder.mkdir()
    (folder / "A_1.fq.gz").write_text("")
    (folder / "A_2.fq.gz").write_text("")
    samples = detect_paired_samples(folder)
    assert len(samples) == 1
    assert samples[0].sample_id == "A"


def test_detect_dot_r1_pattern(tmp_path: Path) -> None:
    folder = tmp_path / "reads"
    folder.mkdir()
    (folder / "B.R1.fastq.gz").write_text("")
    (folder / "B.R2.fastq.gz").write_text("")
    samples = detect_paired_samples(folder)
    assert len(samples) == 1
    assert samples[0].sample_id == "B"


def test_empty_folder_raises(tmp_path: Path) -> None:
    folder = tmp_path / "empty"
    folder.mkdir()
    with pytest.raises(ScanError, match="No FASTQ files"):
        detect_paired_samples(folder)


def test_unpaired_file_raises(tmp_path: Path) -> None:
    folder = tmp_path / "reads"
    folder.mkdir()
    (folder / "S1_R1.fq.gz").write_text("")
    with pytest.raises(ScanError, match="without a matching mate"):
        detect_paired_samples(folder)

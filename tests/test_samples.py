"""Tests for samples.csv loading."""

from pathlib import Path

import pytest

from ecometa_flow.samples import load_samples_csv
from ecometa_flow.scanner import ScanError


@pytest.fixture
def sample_setup(tmp_path: Path) -> tuple[Path, Path]:
    """Create FASTQ files and a samples.csv."""
    reads = tmp_path / "raw_reads"
    reads.mkdir()
    (reads / "S1_R1.fq.gz").write_text("")
    (reads / "S1_R2.fq.gz").write_text("")

    csv_path = tmp_path / "samples.csv"
    csv_path.write_text(
        "SampleID,R1,R2,Group\n"
        "S1,S1_R1.fq.gz,S1_R2.fq.gz,RW\n"
    )
    return csv_path, reads


def test_load_samples_csv(sample_setup: tuple[Path, Path]) -> None:
    csv_path, reads = sample_setup
    samples = load_samples_csv(csv_path, base_dir=reads)
    assert len(samples) == 1
    assert samples[0].sample_id == "S1"
    assert samples[0].r1.name == "S1_R1.fq.gz"
    assert samples[0].r2.name == "S1_R2.fq.gz"


def test_missing_columns_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("SampleID,R1\nS1,file1.fq.gz\n")
    with pytest.raises(ScanError, match="missing required columns"):
        load_samples_csv(csv_path)

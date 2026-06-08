"""Tests for dry-run command generation."""

from pathlib import Path

from ecometa_flow.commands import generate_script_contents
from ecometa_flow.scanner import Sample


def _sample() -> Sample:
    """Create a representative paired-end sample for command rendering tests."""
    return Sample(
        sample_id="S1",
        r1=Path("/data/raw_reads/S1_R1.fq.gz"),
        r2=Path("/data/raw_reads/S1_R2.fq.gz"),
    )


def _envs() -> dict[str, object]:
    """Build an envs.yaml-like structure with mixed command and conda tools."""
    return {
        "tools": {
            "trimmomatic": {
                "mode": "conda",
                "env": "/envs/trimmomatic",
                "command": "trimmomatic",
            },
            "megahit": {"mode": "command", "command": "megahit"},
            "virsorter2": {
                "mode": "conda",
                "env": "/envs/virsorter2",
                "command": "virsorter2",
            },
            "genomad": {"mode": "command", "command": "genomad"},
            "vibrant": {"mode": "command", "command": "VIBRANT_run.py"},
            "checkv": {"mode": "command", "command": "checkv"},
            "bowtie2": {"mode": "command", "command": "bowtie2"},
            "samtools": {"mode": "command", "command": "samtools"},
            "basalt": {"mode": "command", "command": "BASALT"},
            "checkm": {"mode": "command", "command": "checkm"},
            "drep": {"mode": "command", "command": "dRep"},
            "gtdbtk": {"mode": "command", "command": "gtdbtk"},
            "coverm": {"mode": "command", "command": "coverm"},
            "kraken2": {"mode": "command", "command": "kraken2"},
            "taxonkit": {"mode": "command", "command": "taxonkit"},
        },
        "databases": {
            "checkv_db": "/db/checkv",
            "kraken2_db": "/db/kraken2",
            "pathogen_db": "/db/pathogen_taxa.txt",
            "gtdbtk_db": "/db/gtdbtk",
        },
    }


def test_virus_prediction_script_contains_realistic_prediction_steps() -> None:
    script = generate_script_contents(
        "virus_prediction",
        "03_virus_prediction.sh",
        [_sample()],
        Path("/work"),
        _envs(),
        threads=16,
    )

    assert "virsorter2 run" in script
    assert 'genomad end-to-end "/work/results/assembly/S1/final.contigs.fa"' in script
    assert 'VIBRANT_run.py -i "/work/results/assembly/S1/final.contigs.fa"' in script
    assert 'checkv end_to_end "/work/results/virus_prediction/S1/virsorter2/final-viral-combined.fa"' in script
    assert 'bowtie2-build "/work/results/virus_prediction/S1/votu/combined_viral_contigs.fa"' in script
    assert 'samtools idxstats "/work/results/mapping/S1/mapped.bam"' in script


def test_mag_qc_script_contains_qc_taxonomy_and_abundance_steps() -> None:
    script = generate_script_contents(
        "mag_pipeline",
        "04_mag_qc.sh",
        [_sample()],
        Path("/work"),
        _envs(),
        threads=8,
    )

    assert 'checkm lineage_wf -t 8 -x fa "/work/results/binning/S1/bins"' in script
    assert 'dRep dereplicate "/work/results/dereplication"' in script
    assert 'GTDBTK_DATA_PATH="/db/gtdbtk" gtdbtk classify_wf' in script
    assert 'coverm genome -1 "/work/results/clean_reads/S1_R1.fastq.gz"' in script


def test_read_based_risk_script_contains_taxonomy_and_pathogen_screening() -> None:
    class_script = generate_script_contents(
        "read_based_risk",
        "02_classification.sh",
        [_sample()],
        Path("/work"),
        _envs(),
        threads=4,
    )
    screen_script = generate_script_contents(
        "read_based_risk",
        "03_pathogen_screening.sh",
        [_sample()],
        Path("/work"),
        _envs(),
        threads=4,
    )

    assert 'kraken2 --db "/db/kraken2" --paired' in class_script
    assert 'taxonkit lineage -i 2' in class_script
    assert 'grep -F -f "/db/pathogen_taxa.txt"' in screen_script
    assert 'print "sample_id","pathogen_hits"' in screen_script


def test_micro_risk_script_contains_integrated_mapping_and_risk_summary() -> None:
    script = generate_script_contents(
        "micro_risk",
        "02_risk_assessment.sh",
        [_sample()],
        Path("/work"),
        _envs(),
        threads=12,
    )

    assert 'trimmomatic PE -threads 12 "/data/raw_reads/S1_R1.fq.gz"' in script
    assert 'ln -sfn "$VIRUS_DIR/results/virus_prediction"' not in script
    assert 'kraken2 --db "/db/kraken2" --paired' in script
    assert 'cat /work/results/integrated_inputs/virus_prediction/*/votu/combined_viral_contigs.fa > "/work/tmp/viral_catalog.fa"' in script
    assert 'bowtie2-build "/work/tmp/viral_catalog.fa" "/work/tmp/viral_catalog"' in script
    assert 'samtools idxstats "/work/results/prokaryotic_risk/S1.bam"' in script
    assert 'print "sample_id","viral_reads","prokaryotic_reads","checkv_db"' in script

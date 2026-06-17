"""Tests for workflow validation and dry-run summaries."""

from __future__ import annotations

from pathlib import Path

from ecometa_flow.cli import main
from ecometa_flow.validation import validate_workflow


def _make_reads(folder: Path) -> Path:
    """Create a small paired-end FASTQ input folder."""
    reads = folder / "raw_reads"
    reads.mkdir()
    for name in ("S1_R1.fq.gz", "S1_R2.fq.gz", "S2_R1.fq.gz", "S2_R2.fq.gz"):
        (reads / name).write_text("", encoding="utf-8")
    return reads


def _make_envs_file(folder: Path) -> Path:
    """Create an envs.yaml that satisfies virus_prediction requirements."""
    envs = folder / "envs.yaml"
    envs.write_text(
        "\n".join([
            "tools:",
            "  trimmomatic: {mode: command, command: trimmomatic}",
            "  megahit: {mode: command, command: megahit}",
            "  virsorter2: {mode: command, command: virsorter}",
            "  genomad: {mode: command, command: genomad}",
            "  vibrant: {mode: command, command: VIBRANT_run.py}",
            "  checkv: {mode: command, command: checkv}",
            "  bowtie2: {mode: command, command: bowtie2}",
            "  samtools: {mode: command, command: samtools}",
            "databases:",
            "  checkv_db: /db/checkv",
            "",
        ]),
        encoding="utf-8",
    )
    return envs


def test_workflow_validation_with_valid_input(tmp_path: Path) -> None:
    reads = _make_reads(tmp_path)
    envs = _make_envs_file(tmp_path)
    work = tmp_path / "work"

    report = validate_workflow(
        module="virus_prediction",
        input_dir=reads,
        work_dir=work,
        samples_path=None,
        params_path=None,
        envs_cli=str(envs),
        threads=8,
        dry_run=True,
        force=False,
    )

    assert report.ok
    assert report.input_dir_exists
    assert report.samples_valid
    assert report.module_supported
    assert report.requirements_loaded
    assert report.envs_found
    assert report.output_dir_ready
    assert len(report.samples) == 2
    assert report.comparison["missing_tools"] == []
    assert report.comparison["missing_databases"] == []


def test_workflow_validation_missing_input_folder(tmp_path: Path) -> None:
    envs = _make_envs_file(tmp_path)

    report = validate_workflow(
        module="virus_prediction",
        input_dir=tmp_path / "missing_reads",
        work_dir=tmp_path / "work",
        samples_path=None,
        params_path=None,
        envs_cli=str(envs),
        threads=4,
        dry_run=True,
        force=False,
    )

    assert not report.ok
    assert not report.input_dir_exists
    assert any("Input folder does not exist" in error for error in report.errors)


def test_workflow_validation_missing_envs_yaml_behavior(
    tmp_path: Path,
    monkeypatch,
) -> None:
    reads = _make_reads(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("ECOMETA_ENVS", raising=False)
    monkeypatch.delenv("ECOMETA_HOME", raising=False)

    report = validate_workflow(
        module="virus_prediction",
        input_dir=reads,
        work_dir=tmp_path / "work",
        samples_path=None,
        params_path=None,
        envs_cli=None,
        threads=4,
        dry_run=True,
        force=False,
    )

    assert report.ok
    assert not report.envs_found
    assert report.envs_path is None
    assert report.comparison["available_tools"] == []
    assert set(report.comparison["missing_tools"]) == set(report.requirements["tools"])
    assert "envs.yaml not found" in report.warnings[0]


def test_workflow_summary_md_creation(tmp_path: Path, capsys) -> None:
    reads = _make_reads(tmp_path)
    envs = _make_envs_file(tmp_path)
    work = tmp_path / "work"

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        str(reads),
        "-o",
        str(work),
        "--envs",
        str(envs),
        "-t",
        "16",
        "--dry-run",
    ])

    output = capsys.readouterr().out
    summary = work / "workflow_summary.md"
    assert exit_code == 0
    assert summary.is_file()
    text = summary.read_text(encoding="utf-8")
    assert "# EcoMetaFlow Workflow Summary" in text
    assert "- Module: virus_prediction" in text
    assert "- params.yaml: (not provided)" in text
    assert "## Effective Parameters" in text
    assert "min_contig_len: 1000" in text
    assert "- Output directory safety check: passed" in text
    assert "- Force: no" in text
    assert "| S1 |" in text
    assert "No external tools were executed in dry-run mode" in text
    assert str(summary) in output


def test_run_with_params_writes_params_path_to_summary(
    tmp_path: Path,
    capsys,
) -> None:
    params = Path("examples/params.yaml").resolve()
    work = tmp_path / "work_with_params"

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        "examples/raw_reads",
        "-o",
        str(work),
        "--envs",
        "examples/envs.yaml",
        "--params",
        str(params),
        "-t",
        "16",
        "--dry-run",
    ])

    capsys.readouterr()
    summary = work / "workflow_summary.md"
    text = summary.read_text(encoding="utf-8")
    assert exit_code == 0
    assert summary.is_file()
    assert f"- params.yaml: {params}" in text
    assert "- params.yaml loaded: yes" in text
    assert "min_contig_len: 200" in text


def test_run_without_params_still_works(tmp_path: Path, capsys) -> None:
    work = tmp_path / "work_without_params"

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        "examples/raw_reads",
        "-o",
        str(work),
        "--envs",
        "examples/envs.yaml",
        "--dry-run",
    ])

    capsys.readouterr()
    summary = work / "workflow_summary.md"
    text = summary.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "- params.yaml: (not provided)" in text
    assert "- params.yaml loaded: not provided" in text


def test_existing_output_directory_fails_without_force(
    tmp_path: Path,
    capsys,
) -> None:
    reads = _make_reads(tmp_path)
    envs = _make_envs_file(tmp_path)
    work = tmp_path / "existing_work"
    work.mkdir()

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        str(reads),
        "-o",
        str(work),
        "--envs",
        str(envs),
        "--dry-run",
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "output directory already exists" in captured.err
    assert "--force" in captured.err


def test_existing_output_directory_succeeds_with_force(
    tmp_path: Path,
    capsys,
) -> None:
    reads = _make_reads(tmp_path)
    envs = _make_envs_file(tmp_path)
    work = tmp_path / "existing_work"
    work.mkdir()

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        str(reads),
        "-o",
        str(work),
        "--envs",
        str(envs),
        "--dry-run",
        "--force",
    ])

    capsys.readouterr()
    summary = work / "workflow_summary.md"
    text = summary.read_text(encoding="utf-8")
    assert exit_code == 0
    assert summary.is_file()
    assert "- Force: yes" in text
    assert "output directory exists and --force allows regeneration" in text


def test_unsafe_output_path_is_refused(capsys) -> None:
    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        "examples/raw_reads",
        "-o",
        str(Path.cwd()),
        "--envs",
        "examples/envs.yaml",
        "--dry-run",
        "--force",
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "project repository root" in captured.err


def test_input_directory_cannot_be_output_directory(capsys) -> None:
    input_dir = Path("examples/raw_reads").resolve()

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        str(input_dir),
        "-o",
        str(input_dir),
        "--envs",
        "examples/envs.yaml",
        "--dry-run",
        "--force",
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "output directory cannot be the input directory" in captured.err


def test_missing_params_file_gives_clear_error(
    tmp_path: Path,
    capsys,
) -> None:
    reads = _make_reads(tmp_path)
    envs = _make_envs_file(tmp_path)

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        str(reads),
        "-o",
        str(tmp_path / "work"),
        "--envs",
        str(envs),
        "--params",
        str(tmp_path / "missing_params.yaml"),
        "--dry-run",
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "params YAML not found" in captured.err


def test_invalid_yaml_params_file_gives_clear_error(
    tmp_path: Path,
    capsys,
) -> None:
    reads = _make_reads(tmp_path)
    envs = _make_envs_file(tmp_path)
    params = tmp_path / "bad_params.yaml"
    params.write_text("trimming: [\n", encoding="utf-8")

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        str(reads),
        "-o",
        str(tmp_path / "work"),
        "--envs",
        str(envs),
        "--params",
        str(params),
        "--dry-run",
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "invalid params YAML" in captured.err


def test_non_dry_run_is_refused_without_executing(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    reads = _make_reads(tmp_path)
    envs = _make_envs_file(tmp_path)
    work = tmp_path / "work"

    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("non-dry-run attempted to execute a generated script")

    monkeypatch.setattr("ecometa_flow.runner.subprocess.run", fail_if_called)

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        str(reads),
        "-o",
        str(work),
        "--envs",
        str(envs),
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Real execution is not enabled in this version" in captured.err
    assert not work.exists()


def test_dry_run_does_not_execute_external_tools(
    tmp_path: Path,
    monkeypatch,
) -> None:
    reads = _make_reads(tmp_path)
    envs = _make_envs_file(tmp_path)

    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("dry-run attempted to execute a generated script")

    monkeypatch.setattr("ecometa_flow.runner.subprocess.run", fail_if_called)

    exit_code = main([
        "run",
        "-m",
        "virus_prediction",
        "-i",
        str(reads),
        "-o",
        str(tmp_path / "work"),
        "--envs",
        str(envs),
        "--dry-run",
    ])

    assert exit_code == 0

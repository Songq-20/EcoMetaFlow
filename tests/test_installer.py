"""Tests for dry-run installation planning."""

from __future__ import annotations

from pathlib import Path

import yaml

from ecometa_flow.cli import main
from ecometa_flow.installer import (
    detect_tools_in_path,
    format_install_report,
    load_install_recipes,
    plan_installation,
    render_envs_template,
    render_install_script,
    run_install,
)
from ecometa_flow.requirements import get_module_requirements


def test_plan_installation_builds_conda_commands_from_existing_env_root() -> None:
    required = get_module_requirements("virus_prediction")
    envs = {
        "tools": {
            "trimmomatic": {
                "mode": "conda",
                "env": "/data/software/ecometa-flow/envs/trimmomatic",
                "command": "trimmomatic",
            },
            "megahit": {"mode": "command", "command": "megahit"},
        },
        "databases": {},
    }

    plan = plan_installation(required, envs, load_install_recipes(), path_tools={})
    tool_entries = {entry["name"]: entry for entry in plan["tools"]}

    assert "genomad" in tool_entries
    assert tool_entries["genomad"]["command"] == (
        'conda create -y -p "/data/software/ecometa-flow/envs/genomad" '
        "bioconda::genomad"
    )
    assert "env: /data/software/ecometa-flow/envs/genomad" in tool_entries["genomad"]["envs_snippet"]


def test_format_install_report_includes_conda_commands_and_database_notes() -> None:
    plan = {
        "tools": [{
            "name": "genomad",
            "action": "Would install tool 'genomad' via dry-run conda planning.",
            "package": "bioconda::genomad",
            "command": 'conda create -y -p "/envs/genomad" bioconda::genomad',
            "envs_snippet": "genomad:\n  mode: conda\n  env: /envs/genomad\n  command: genomad",
        }],
        "databases": [{
            "name": "checkv_db",
            "action": "Would register database 'checkv_db' after manual preparation.",
            "note": "Database download will be implemented in a future version.",
        }],
        "available_tools_envs": [],
        "tools_found_path": [],
        "available_databases_envs": [],
    }

    report = format_install_report(
        module="virus_prediction",
        install_all=False,
        plan=plan,
        envs_path=Path("/tmp/envs.yaml"),
        dry_run=True,
    )

    assert 'dry-run conda command: conda create -y -p "/envs/genomad" bioconda::genomad' in report
    assert "suggested envs.yaml entry:" in report
    assert "Database download will be implemented in a future version." in report


def test_run_install_uses_env_file_to_reduce_install_plan(tmp_path: Path) -> None:
    envs_path = tmp_path / "envs.yaml"
    envs_path.write_text(
        "tools:\n"
        "  trimmomatic:\n"
        "    mode: conda\n"
        "    env: /opt/ecometa/envs/trimmomatic\n"
        "    command: trimmomatic\n"
        "  megahit:\n"
        "    mode: command\n"
        "    command: megahit\n"
        "  virsorter2:\n"
        "    mode: command\n"
        "    command: virsorter2\n"
        "databases:\n"
        "  checkv_db: /db/checkv\n",
        encoding="utf-8",
    )

    report = run_install(
        module="virus_prediction",
        install_all=False,
        envs_cli=str(envs_path),
        dry_run=True,
    )

    assert "trimmomatic" not in report.split("Tools to install:")[1]
    assert 'conda create -y -p "/opt/ecometa/envs/genomad" bioconda::genomad' in report
    assert "No installation was performed." in report


def test_detect_tools_in_path_uses_shutil_which(monkeypatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "megahit":
            return "/usr/local/bin/megahit"
        return None

    monkeypatch.setattr("ecometa_flow.installer.shutil.which", fake_which)

    found = detect_tools_in_path(["trimmomatic", "megahit"])
    assert found == {"megahit": "/usr/local/bin/megahit"}


def test_install_dry_run_reports_found_and_missing_tools(
    tmp_path: Path,
    monkeypatch,
) -> None:
    envs_path = tmp_path / "envs.yaml"
    envs_path.write_text(
        "tools:\n"
        "  trimmomatic:\n"
        "    mode: command\n"
        "    command: trimmomatic\n"
        "databases: {}\n",
        encoding="utf-8",
    )

    def fake_which(name: str) -> str | None:
        if name == "megahit":
            return "/usr/bin/megahit"
        return None

    monkeypatch.setattr("ecometa_flow.installer.shutil.which", fake_which)

    report = run_install(
        module="virus_prediction",
        install_all=False,
        envs_cli=str(envs_path),
        dry_run=True,
    )

    assert "Tools already configured in envs.yaml:" in report
    assert "  - trimmomatic" in report
    assert "Tools found in PATH:" in report
    assert "  - megahit: /usr/bin/megahit" in report
    assert "  - genomad: Would install tool 'genomad'" in report
    assert "checkv_db" in report
    assert "No installation was performed." in report


def test_render_install_script_contains_review_only_conda_commands() -> None:
    plan = {
        "tools": [{
            "name": "genomad",
            "installer": "conda",
            "command": 'conda create -y -p "/envs/genomad" bioconda::genomad',
        }],
        "databases": [{
            "name": "checkv_db",
            "action": "Would register database after manual preparation.",
        }],
    }

    script = render_install_script(plan)
    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail")
    assert "Review this script before running it manually" in script
    assert 'conda create -y -p "/envs/genomad" bioconda::genomad' in script
    assert "download" not in script.lower().replace("no database downloads", "")


def test_render_envs_template_contains_path_and_placeholders() -> None:
    plan = {
        "tools": [{
            "name": "genomad",
        }],
        "databases": [{
            "name": "checkv_db",
        }],
        "tools_found_path": [{
            "name": "megahit",
            "path": "/usr/bin/megahit",
        }],
    }

    template = render_envs_template(plan)
    data = yaml.safe_load(template)
    assert data["tools"]["megahit"]["mode"] == "command"
    assert data["tools"]["genomad"]["mode"] == "conda"
    assert data["tools"]["genomad"]["env"] == "/path/to/ecometa-flow/envs/genomad"
    assert data["databases"]["checkv_db"] == "/path/to/checkv_db"
    assert "did not download" in template


def test_write_script_and_envs_create_review_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    script = tmp_path / "bootstrap.sh"
    envs = tmp_path / "envs.yaml"

    monkeypatch.setattr("ecometa_flow.installer.shutil.which", lambda name: None)

    report = run_install(
        module="virus_prediction",
        install_all=False,
        envs_cli=None,
        dry_run=True,
        write_script=script,
        write_envs=envs,
        force=False,
    )

    script_text = script.read_text(encoding="utf-8")
    envs_text = envs.read_text(encoding="utf-8")
    assert script.is_file()
    assert envs.is_file()
    assert script_text.startswith("#!/usr/bin/env bash")
    assert "conda create" in script_text
    assert "checkv_db: /path/to/checkv_db" in envs_text
    assert "Generated review files:" in report
    assert "No installation was performed." in report


def test_existing_bootstrap_files_not_overwritten_without_force(
    tmp_path: Path,
    monkeypatch,
) -> None:
    script = tmp_path / "bootstrap.sh"
    script.write_text("keep me\n", encoding="utf-8")
    monkeypatch.setattr("ecometa_flow.installer.shutil.which", lambda name: None)

    exit_code = main([
        "install",
        "--module",
        "virus_prediction",
        "--dry-run",
        "--write-script",
        str(script),
    ])

    assert exit_code == 1
    assert script.read_text(encoding="utf-8") == "keep me\n"


def test_existing_bootstrap_files_can_be_overwritten_with_force(
    tmp_path: Path,
    monkeypatch,
) -> None:
    script = tmp_path / "bootstrap.sh"
    script.write_text("replace me\n", encoding="utf-8")
    monkeypatch.setattr("ecometa_flow.installer.shutil.which", lambda name: None)

    exit_code = main([
        "install",
        "--module",
        "virus_prediction",
        "--dry-run",
        "--write-script",
        str(script),
        "--force",
    ])

    assert exit_code == 0
    assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")


def test_no_external_conda_commands_are_executed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("install attempted to execute an external command")

    monkeypatch.setattr("ecometa_flow.installer.shutil.which", lambda name: None)
    monkeypatch.setattr("subprocess.run", fail_if_called)

    report = run_install(
        module="virus_prediction",
        install_all=False,
        envs_cli=None,
        dry_run=True,
        write_script=tmp_path / "bootstrap.sh",
        force=False,
    )

    assert "No installation was performed." in report
    assert "No database download was performed." in report

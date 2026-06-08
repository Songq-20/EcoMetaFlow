"""Tests for dry-run installation planning."""

from pathlib import Path

from ecometa_flow.installer import (
    format_install_report,
    load_install_recipes,
    plan_installation,
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

    plan = plan_installation(required, envs, load_install_recipes())
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
    assert "No installation or download was executed in this version." in report

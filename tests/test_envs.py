"""Tests for envs.yaml loading and comparison."""

from pathlib import Path

import yaml

from ecometa_flow.envs import (
    compare_requirements,
    load_envs,
    resolve_envs_path,
    resolve_tool_command,
)


def test_resolve_envs_cli_priority(tmp_path: Path, monkeypatch) -> None:
    envs_file = tmp_path / "custom_envs.yaml"
    envs_file.write_text("tools: {}\ndatabases: {}\n")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "envs.yaml").write_text("tools: {}\ndatabases: {}\n")

    resolved = resolve_envs_path(str(envs_file))
    assert resolved == envs_file.resolve()


def test_load_envs_parses_tools_and_databases(tmp_path: Path) -> None:
    envs_file = tmp_path / "envs.yaml"
    envs_file.write_text(yaml.dump({
        "tools": {"megahit": {"mode": "command", "command": "megahit"}},
        "databases": {"checkv_db": "/db/checkv"},
    }))
    envs = load_envs(envs_file)
    assert "megahit" in envs["tools"]
    assert envs["databases"]["checkv_db"] == "/db/checkv"


def test_compare_requirements_lists_missing() -> None:
    envs = {"tools": {"megahit": {}}, "databases": {}}
    result = compare_requirements(
        ["megahit", "checkv"],
        ["checkv_db", "kraken2_db"],
        envs,
    )
    assert result["available_tools"] == ["megahit"]
    assert result["missing_tools"] == ["checkv"]
    assert result["missing_databases"] == ["checkv_db", "kraken2_db"]


def test_resolve_tool_command_conda() -> None:
    entry = {"mode": "conda", "env": "/envs/trimmomatic", "command": "trimmomatic"}
    cmd = resolve_tool_command("trimmomatic", entry)
    assert "conda run" in cmd
    assert "trimmomatic" in cmd


def test_resolve_tool_command_direct() -> None:
    entry = {"mode": "command", "command": "megahit"}
    assert resolve_tool_command("megahit", entry) == "megahit"

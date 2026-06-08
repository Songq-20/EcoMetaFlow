"""Find, load, and validate envs.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from ecometa_flow.config import get_ecometa_home


def resolve_envs_path(cli_path: str | None = None) -> Path | None:
    """
    Find envs.yaml using the lookup priority defined in the design doc.

    Priority:
      1. --envs CLI argument
      2. $ECOMETA_ENVS
      3. ./envs.yaml
      4. ~/.ecometa-flow/envs.yaml
      5. $ECOMETA_HOME/config/envs.yaml
    """
    candidates: list[Path] = []

    if cli_path:
        candidates.append(Path(cli_path).expanduser())

    env_var = os.environ.get("ECOMETA_ENVS")
    if env_var:
        candidates.append(Path(env_var).expanduser())

    candidates.append(Path.cwd() / "envs.yaml")
    candidates.append(Path.home() / ".ecometa-flow" / "envs.yaml")

    ecometa_home = get_ecometa_home()
    if ecometa_home:
        candidates.append(ecometa_home / "config" / "envs.yaml")

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    return None


def load_envs(path: Path | None = None) -> dict[str, Any]:
    """Load envs.yaml; return empty structure if the file is missing."""
    if path is None:
        return {"tools": {}, "databases": {}}

    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    return {
        "tools": data.get("tools", {}) or {},
        "databases": data.get("databases", {}) or {},
    }


def resolve_tool_command(tool_name: str, tool_entry: dict[str, Any]) -> str:
    """
    Build the shell command prefix for a tool entry.

    Supports mode: command (direct call) and mode: conda (conda run -p env).
    """
    mode = tool_entry.get("mode", "command")
    command = tool_entry.get("command", tool_name)

    if mode == "conda":
        env_path = tool_entry.get("env", "")
        return f'conda run -p "{env_path}" {command}'

    return command


def compare_requirements(
    required_tools: list[str],
    required_databases: list[str],
    envs: dict[str, Any],
) -> dict[str, list[str]]:
    """Compare module requirements against envs.yaml and list gaps."""
    available_tools = set(envs.get("tools", {}).keys())
    available_databases = set(envs.get("databases", {}).keys())

    return {
        "available_tools": sorted(available_tools & set(required_tools)),
        "missing_tools": sorted(set(required_tools) - available_tools),
        "available_databases": sorted(available_databases & set(required_databases)),
        "missing_databases": sorted(set(required_databases) - available_databases),
    }


def format_check_report(
    module: str,
    required: dict[str, list[str]],
    comparison: dict[str, list[str]],
    envs_path: Path | None,
) -> str:
    """Build a human-readable environment check report."""
    lines = [f"Environment check for module: {module}", ""]

    if envs_path:
        lines.append(f"envs.yaml: {envs_path}")
    else:
        lines.append("envs.yaml: not found (all tools/databases reported as missing)")
    lines.append("")

    lines.append("Required tools:")
    for tool in required["tools"]:
        lines.append(f"  - {tool}")
    lines.append("")

    lines.append("Required databases:")
    for db in required["databases"]:
        lines.append(f"  - {db}")
    lines.append("")

    lines.append("Available tools:")
    if comparison["available_tools"]:
        for tool in comparison["available_tools"]:
            lines.append(f"  - {tool}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Available databases:")
    if comparison["available_databases"]:
        for db in comparison["available_databases"]:
            lines.append(f"  - {db}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Missing tools:")
    if comparison["missing_tools"]:
        for tool in comparison["missing_tools"]:
            lines.append(f"  - {tool}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Missing databases:")
    if comparison["missing_databases"]:
        for db in comparison["missing_databases"]:
            lines.append(f"  - {db}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)

"""Dry-run installation planning for missing tools and databases."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import yaml

from ecometa_flow.config import package_data_path
from ecometa_flow.envs import load_envs, resolve_envs_path
from ecometa_flow.requirements import (
    get_module_requirements,
    list_all_tools_and_databases,
    load_requirements,
)


def load_install_recipes(path: Path | None = None) -> dict[str, Any]:
    """Load built-in install recipes from install.yaml."""
    install_path = path or package_data_path("install.yaml")
    with install_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def collect_requirements_for_install(
    module: str | None,
    install_all: bool,
    requirements: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Gather tools and databases needed for install --module or install --all."""
    data = requirements or load_requirements()

    if install_all:
        return list_all_tools_and_databases(data)

    if module is None:
        raise ValueError("Specify --module MODULE or use --all.")

    return get_module_requirements(module, data)


def infer_conda_env_root(envs: dict[str, Any]) -> Path:
    """Infer a reusable conda env root from envs.yaml or fall back to a local default."""
    conda_envs: list[Path] = []
    for entry in envs.get("tools", {}).values():
        if entry.get("mode") == "conda" and entry.get("env"):
            conda_envs.append(Path(str(entry["env"])).expanduser())

    if conda_envs:
        return conda_envs[0].parent

    return Path.home() / ".ecometa-flow" / "envs"


def build_tool_install_command(
    tool: str,
    recipe: dict[str, Any],
    env_root: Path,
) -> tuple[str, str]:
    """Build a dry-run conda install command and the matching envs.yaml snippet."""
    env_path = env_root / tool
    package = recipe.get("package", tool)
    binary = tool
    if tool == "gtdbtk":
        binary = "gtdbtk"

    command = f'conda create -y -p "{env_path}" {package}'
    envs_snippet = (
        f"{tool}:\n"
        "  mode: conda\n"
        f"  env: {env_path}\n"
        f"  command: {binary}"
    )
    return command, envs_snippet


def detect_tools_in_path(required_tools: list[str]) -> dict[str, str]:
    """Return required tools that can be found on PATH."""
    found: dict[str, str] = {}
    for tool in required_tools:
        resolved = shutil.which(tool)
        if resolved:
            found[tool] = resolved
    return found


def plan_installation(
    required: dict[str, list[str]],
    envs: dict[str, Any],
    recipes: dict[str, Any],
    path_tools: dict[str, str] | None = None,
) -> dict[str, list[dict[str, str]]]:
    """
    Compare requirements with envs.yaml and return dry-run install actions.

    Returns dict with keys 'tools' and 'databases', each a list of plan entries.
    """
    available_tools = set(envs.get("tools", {}).keys())
    available_databases = set(envs.get("databases", {}).keys())
    path_tools = path_tools or {}
    env_root = infer_conda_env_root(envs)

    tool_recipes = recipes.get("tools", {})
    db_recipes = recipes.get("databases", {})

    tool_plans: list[dict[str, str]] = []
    for tool in required["tools"]:
        if tool in available_tools or tool in path_tools:
            continue
        recipe = tool_recipes.get(tool, {})
        install_cmd, envs_snippet = build_tool_install_command(tool, recipe, env_root)
        tool_plans.append({
            "name": tool,
            "installer": recipe.get("installer", "unknown"),
            "package": recipe.get("package", tool),
            "command": install_cmd,
            "envs_snippet": envs_snippet,
            "action": f"Would install tool '{tool}' via dry-run conda planning.",
        })

    db_plans: list[dict[str, str]] = []
    for db in required["databases"]:
        if db in available_databases:
            continue
        recipe = db_recipes.get(db, {})
        db_plans.append({
            "name": db,
            "installer": recipe.get("installer", "unknown"),
            "note": recipe.get("note", "not defined"),
            "action": f"Would register database '{db}' after manual preparation.",
        })

    return {
        "tools": tool_plans,
        "databases": db_plans,
        "available_tools_envs": [
            {"name": tool, "source": "envs.yaml"}
            for tool in sorted(set(required["tools"]) & available_tools)
        ],
        "tools_found_path": [
            {"name": tool, "path": path_tools[tool]}
            for tool in sorted(set(required["tools"]) & set(path_tools))
        ],
        "available_databases_envs": [
            {"name": db, "source": "envs.yaml"}
            for db in sorted(set(required["databases"]) & available_databases)
        ],
    }


def _plan_entries(plan: dict[str, list[dict[str, str]]], key: str) -> list[dict[str, str]]:
    """Return a plan list while tolerating older test fixtures."""
    return plan.get(key, [])


def render_install_script(plan: dict[str, list[dict[str, str]]]) -> str:
    """Render a review-only shell script with suggested conda commands."""
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# EcoMetaFlow bootstrap plan.",
        "# Review this script before running it manually.",
        "# No database downloads are included.",
        "",
    ]

    tool_entries = [
        entry for entry in plan["tools"] if entry.get("installer") == "conda"
    ]
    if tool_entries:
        for entry in tool_entries:
            lines.append(f"# Suggested environment for {entry['name']}")
            lines.append(entry["command"])
            lines.append("")
    else:
        lines.append("# No missing tools with known conda recipes.")
        lines.append("")

    return "\n".join(lines)


def render_envs_template(plan: dict[str, list[dict[str, str]]]) -> str:
    """Render an envs.yaml template from PATH hits and missing requirements."""
    tools: dict[str, Any] = {}
    databases: dict[str, str] = {}

    for entry in _plan_entries(plan, "tools_found_path"):
        tools[entry["name"]] = {
            "mode": "command",
            "command": entry["name"],
        }

    for entry in plan["tools"]:
        tools[entry["name"]] = {
            "mode": "conda",
            "env": f"/path/to/ecometa-flow/envs/{entry['name']}",
            "command": entry["name"],
        }

    for entry in plan["databases"]:
        databases[entry["name"]] = f"/path/to/{entry['name']}"

    template = {
        "tools": tools,
        "databases": databases,
    }
    header = (
        "# EcoMetaFlow envs.yaml template.\n"
        "# Review and replace placeholder paths before running workflows.\n"
        "# Databases are placeholders only; EcoMetaFlow did not download them.\n"
    )
    return header + yaml.safe_dump(template, sort_keys=False)


def _write_text_file(path: Path, text: str, force: bool) -> None:
    """Write a generated bootstrap file with overwrite protection."""
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}. Use --force.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bootstrap_files(
    plan: dict[str, list[dict[str, str]]],
    write_script: Path | None,
    write_envs: Path | None,
    force: bool,
) -> list[Path]:
    """Write optional review-only bootstrap artifacts."""
    written: list[Path] = []
    if write_script:
        _write_text_file(write_script, render_install_script(plan), force)
        write_script.chmod(0o755)
        written.append(write_script)
    if write_envs:
        _write_text_file(write_envs, render_envs_template(plan), force)
        written.append(write_envs)
    return written


def format_install_report(
    module: str | None,
    install_all: bool,
    plan: dict[str, list[dict[str, str]]],
    envs_path: Path | None,
    dry_run: bool,
) -> str:
    """Build a human-readable dry-run install report."""
    target = "all modules" if install_all else f"module '{module}'"
    mode = "DRY-RUN" if dry_run else "REPORT-ONLY"

    lines = [
        f"EcoMetaFlow install plan ({mode})",
        f"Target: {target}",
        "",
    ]

    if envs_path:
        lines.append(f"envs.yaml: {envs_path}")
    else:
        lines.append("envs.yaml: not found")
    lines.append("")

    lines.append("Tools already configured in envs.yaml:")
    env_tool_entries = _plan_entries(plan, "available_tools_envs")
    if env_tool_entries:
        for entry in env_tool_entries:
            lines.append(f"  - {entry['name']}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Tools found in PATH:")
    path_tool_entries = _plan_entries(plan, "tools_found_path")
    if path_tool_entries:
        for entry in path_tool_entries:
            lines.append(f"  - {entry['name']}: {entry['path']}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("Tools to install:")
    if plan["tools"]:
        for entry in plan["tools"]:
            lines.append(f"  - {entry['name']}: {entry['action']}")
            lines.append(f"      package: {entry['package']}")
            lines.append(f"      dry-run conda command: {entry['command']}")
            lines.append("      suggested envs.yaml entry:")
            for snippet_line in entry["envs_snippet"].splitlines():
                lines.append(f"        {snippet_line}")
    else:
        lines.append("  (none - no missing tools after envs.yaml/PATH checks)")
    lines.append("")

    lines.append("Databases to prepare:")
    if plan["databases"]:
        for entry in plan["databases"]:
            lines.append(f"  - {entry['name']}: {entry['action']}")
            if entry.get("note"):
                lines.append(f"      note: {entry['note']}")
    else:
        lines.append("  (none - all required databases already in envs.yaml)")
    lines.append("")

    available_db_entries = _plan_entries(plan, "available_databases_envs")
    lines.append("Databases already configured in envs.yaml:")
    if available_db_entries:
        for entry in available_db_entries:
            lines.append(f"  - {entry['name']}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("No installation was performed.")
    lines.append("No database download was performed.")
    return "\n".join(lines)


def run_install(
    module: str | None,
    install_all: bool,
    envs_cli: str | None,
    dry_run: bool = True,
    write_script: Path | None = None,
    write_envs: Path | None = None,
    force: bool = False,
) -> str:
    """Execute install planning and return the report text."""
    required = collect_requirements_for_install(module, install_all)
    envs_path = resolve_envs_path(envs_cli)
    envs = load_envs(envs_path)
    recipes = load_install_recipes()
    path_tools = detect_tools_in_path(required["tools"])
    plan = plan_installation(required, envs, recipes, path_tools)
    written = write_bootstrap_files(plan, write_script, write_envs, force)

    report = format_install_report(module, install_all, plan, envs_path, dry_run)
    if written:
        report_lines = [report, "", "Generated review files:"]
        for path in written:
            report_lines.append(f"  - {path}")
        report_lines.append("")
        report_lines.append("Review generated files before running any commands manually.")
        return "\n".join(report_lines)

    return report

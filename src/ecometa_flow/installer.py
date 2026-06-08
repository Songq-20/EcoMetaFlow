"""Dry-run installation planning for missing tools and databases."""

from __future__ import annotations

from pathlib import Path
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


def plan_installation(
    required: dict[str, list[str]],
    envs: dict[str, Any],
    recipes: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    """
    Compare requirements with envs.yaml and return dry-run install actions.

    Returns dict with keys 'tools' and 'databases', each a list of plan entries.
    """
    available_tools = set(envs.get("tools", {}).keys())
    available_databases = set(envs.get("databases", {}).keys())
    env_root = infer_conda_env_root(envs)

    tool_recipes = recipes.get("tools", {})
    db_recipes = recipes.get("databases", {})

    tool_plans: list[dict[str, str]] = []
    for tool in required["tools"]:
        if tool in available_tools:
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

    return {"tools": tool_plans, "databases": db_plans}


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
        lines.append("  (none — all required tools already in envs.yaml)")
    lines.append("")

    lines.append("Databases to prepare:")
    if plan["databases"]:
        for entry in plan["databases"]:
            lines.append(f"  - {entry['name']}: {entry['action']}")
            if entry.get("note"):
                lines.append(f"      note: {entry['note']}")
    else:
        lines.append("  (none — all required databases already in envs.yaml)")
    lines.append("")

    lines.append("No installation or download was executed in this version.")
    return "\n".join(lines)


def run_install(
    module: str | None,
    install_all: bool,
    envs_cli: str | None,
    dry_run: bool = True,
) -> str:
    """Execute install planning and return the report text."""
    required = collect_requirements_for_install(module, install_all)
    envs_path = resolve_envs_path(envs_cli)
    envs = load_envs(envs_path)
    recipes = load_install_recipes()
    plan = plan_installation(required, envs, recipes)

    return format_install_report(module, install_all, plan, envs_path, dry_run)

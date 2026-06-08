"""Load built-in module requirements from requirements.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ecometa_flow.config import MODULE_NAMES, package_data_path


def load_requirements(path: Path | None = None) -> dict[str, Any]:
    """Load the requirements YAML (built-in by default)."""
    req_path = path or package_data_path("requirements.yaml")
    with req_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def get_module_requirements(
    module: str, requirements: dict[str, Any] | None = None
) -> dict[str, list[str]]:
    """Return tools and databases required by a module."""
    if module not in MODULE_NAMES:
        raise ValueError(
            f"Unknown module '{module}'. "
            f"Choose one of: {', '.join(MODULE_NAMES)}"
        )

    data = requirements or load_requirements()
    modules = data.get("modules", {})
    if module not in modules:
        raise ValueError(f"Module '{module}' not found in requirements.yaml")

    entry = modules[module]
    return {
        "tools": list(entry.get("tools", [])),
        "databases": list(entry.get("databases", [])),
    }


def list_all_tools_and_databases(
    requirements: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Collect every unique tool and database across all modules."""
    data = requirements or load_requirements()
    tools: set[str] = set()
    databases: set[str] = set()

    for entry in data.get("modules", {}).values():
        tools.update(entry.get("tools", []))
        databases.update(entry.get("databases", []))

    return {
        "tools": sorted(tools),
        "databases": sorted(databases),
    }

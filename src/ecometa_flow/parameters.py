"""Load and merge workflow parameters."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_PARAMETERS: dict[str, Any] = {
    "global": {
        "threads": None,
        "dry_run": True,
    },
    "trimming": {
        "tool": "trimmomatic",
        "leading": 3,
        "trailing": 3,
        "slidingwindow": "4:15",
        "minlen": 36,
    },
    "assembly": {
        "tool": "megahit",
        "min_contig_len": 1000,
    },
    "virus_prediction": {
        "enabled_tools": [
            "virsorter2",
            "genomad",
            "vibrant",
        ],
    },
    "mag_pipeline": {
        "binning_tool": "basalt",
    },
    "read_based_risk": {
        "classifier": "kraken2",
    },
    "micro_risk": {
        "enabled": True,
    },
}


class ParameterError(Exception):
    """Raised when params.yaml cannot be loaded or validated."""


def _deep_merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge nested dictionaries with user values taking precedence."""
    merged = deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_effective_parameters(params_path: Path | None) -> tuple[dict[str, Any], bool]:
    """Load params YAML if provided and merge it with built-in defaults."""
    if params_path is None:
        return deepcopy(DEFAULT_PARAMETERS), False

    if not params_path.is_file():
        raise ParameterError(f"params YAML not found: {params_path}")

    try:
        with params_path.open(encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ParameterError(f"invalid params YAML: {params_path}: {exc}") from exc
    except OSError as exc:
        raise ParameterError(f"could not read params YAML: {params_path}: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ParameterError(f"params YAML must contain a mapping at the top level: {params_path}")

    return _deep_merge(DEFAULT_PARAMETERS, loaded), True

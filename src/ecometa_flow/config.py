"""Project-wide constants and path helpers."""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

# Supported workflow module names.
MODULE_NAMES = (
    "virus_prediction",
    "mag_pipeline",
    "read_based_risk",
    "micro_risk",
)

# FASTQ file extensions scanned in input folders.
FASTQ_GLOBS = ("*.fq.gz", "*.fastq.gz", "*.fq", "*.fastq")

# Default number of threads when the user does not specify -t.
DEFAULT_THREADS = 4


def package_data_path(filename: str) -> Path:
    """Return the path to a built-in YAML file shipped with the package."""
    return Path(resources.files("ecometa_flow.data") / filename)


def get_ecometa_home() -> Path | None:
    """Return ECOMETA_HOME if set, otherwise None."""
    home = os.environ.get("ECOMETA_HOME")
    if home:
        return Path(home).expanduser()
    return None

"""Create work directories, write scripts, and optionally execute them."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ecometa_flow.commands import generate_script_contents
from ecometa_flow.modules import MODULE_SCRIPTS, get_work_directories
from ecometa_flow.scanner import Sample


def create_work_directories(module: str, work_dir: Path) -> None:
    """Create the standard work directory tree for a module."""
    for directory in get_work_directories(module, work_dir):
        directory.mkdir(parents=True, exist_ok=True)


def write_scripts(
    module: str,
    work_dir: Path,
    samples: list[Sample],
    envs: dict[str, Any],
    threads: int,
) -> list[Path]:
    """Generate shell scripts under work_dir/scripts/ and return their paths."""
    scripts_dir = work_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for script_name in MODULE_SCRIPTS.get(module, []):
        content = generate_script_contents(
            module, script_name, samples, work_dir, envs, threads
        )
        script_path = scripts_dir / script_name
        script_path.write_text(content, encoding="utf-8")
        script_path.chmod(0o755)
        written.append(script_path)

    return written


def run_scripts(script_paths: list[Path], dry_run: bool) -> None:
    """
    Execute shell scripts in order, or print them when dry_run is True.

    In v0.1.0, dry_run is the recommended default behaviour.
    """
    for script_path in script_paths:
        if dry_run:
            print(f"\n# --- {script_path.name} ---")
            print(script_path.read_text(encoding="utf-8"))
        else:
            print(f"Running {script_path} ...")
            subprocess.run(
                ["bash", str(script_path)],
                check=True,
            )

"""Workflow validation helpers for run planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ecometa_flow.config import MODULE_NAMES
from ecometa_flow.envs import compare_requirements, load_envs, resolve_envs_path
from ecometa_flow.modules import MODULE_SCRIPTS
from ecometa_flow.requirements import get_module_requirements, load_requirements
from ecometa_flow.samples import load_samples_csv
from ecometa_flow.scanner import Sample, ScanError, detect_paired_samples


@dataclass
class WorkflowValidation:
    """Collected validation details for one planned workflow run."""

    module: str
    input_dir: Path
    work_dir: Path
    samples_path: Path | None
    params_path: Path | None
    threads: int
    dry_run: bool
    samples: list[Sample] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    requirements: dict[str, list[str]] = field(
        default_factory=lambda: {"tools": [], "databases": []}
    )
    envs: dict[str, Any] = field(default_factory=lambda: {"tools": {}, "databases": {}})
    envs_path: Path | None = None
    comparison: dict[str, list[str]] = field(
        default_factory=lambda: {
            "available_tools": [],
            "missing_tools": [],
            "available_databases": [],
            "missing_databases": [],
        }
    )
    generated_scripts: list[Path] = field(default_factory=list)
    input_dir_exists: bool = False
    samples_valid: bool = False
    module_supported: bool = False
    params_loaded: bool = False
    requirements_loaded: bool = False
    envs_found: bool = False
    output_dir_ready: bool = False
    script_list_complete: bool = False
    dry_run_safe: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when the workflow can be planned."""
        return not self.errors


def validate_workflow(
    module: str,
    input_dir: Path,
    work_dir: Path,
    samples_path: Path | None,
    params_path: Path | None,
    envs_cli: str | None,
    threads: int,
    dry_run: bool,
) -> WorkflowValidation:
    """Validate inputs and configuration before scripts are generated."""
    report = WorkflowValidation(
        module=module,
        input_dir=input_dir,
        work_dir=work_dir,
        samples_path=samples_path,
        params_path=params_path,
        threads=threads,
        dry_run=dry_run,
        dry_run_safe=dry_run,
    )

    report.input_dir_exists = input_dir.is_dir()
    if not report.input_dir_exists:
        report.errors.append(f"Input folder does not exist: {input_dir}")

    report.module_supported = module in MODULE_NAMES
    if not report.module_supported:
        report.errors.append(
            f"Unsupported module '{module}'. Choose one of: {', '.join(MODULE_NAMES)}"
        )

    try:
        requirements_data = load_requirements()
        report.requirements_loaded = True
        if report.module_supported:
            report.requirements = get_module_requirements(module, requirements_data)
    except (OSError, ValueError) as exc:
        report.errors.append(f"Could not load requirements.yaml: {exc}")

    if report.input_dir_exists:
        try:
            if samples_path:
                report.samples = load_samples_csv(samples_path, base_dir=input_dir)
            else:
                report.samples = detect_paired_samples(input_dir)
            report.samples_valid = True
        except ScanError as exc:
            report.errors.append(str(exc))

    if params_path:
        if params_path.is_file():
            try:
                with params_path.open(encoding="utf-8") as handle:
                    report.params = yaml.safe_load(handle) or {}
                report.params_loaded = True
            except yaml.YAMLError as exc:
                report.errors.append(f"Could not parse params YAML: {params_path}: {exc}")
            except OSError as exc:
                report.errors.append(f"Could not read params YAML: {params_path}: {exc}")
        else:
            report.warnings.append(f"params YAML not found: {params_path}")

    report.envs_path = resolve_envs_path(envs_cli)
    report.envs_found = report.envs_path is not None
    if not report.envs_found:
        report.warnings.append(
            "envs.yaml not found; all requirements are treated as missing."
        )
    report.envs = load_envs(report.envs_path)

    report.comparison = compare_requirements(
        report.requirements["tools"],
        report.requirements["databases"],
        report.envs,
    )

    if report.ok:
        try:
            work_dir.mkdir(parents=True, exist_ok=True)
            report.output_dir_ready = work_dir.is_dir()
        except OSError as exc:
            report.errors.append(f"Output directory cannot be created: {work_dir}: {exc}")

    return report


def validate_generated_scripts(
    report: WorkflowValidation,
    script_paths: list[Path],
) -> WorkflowValidation:
    """Record generated script paths and check them against the module plan."""
    report.generated_scripts = script_paths
    expected = MODULE_SCRIPTS.get(report.module, [])
    actual_names = [path.name for path in script_paths if path.is_file()]
    report.script_list_complete = actual_names == expected

    if not report.script_list_complete:
        missing = [name for name in expected if name not in actual_names]
        unexpected = [name for name in actual_names if name not in expected]
        if missing:
            report.errors.append(f"Generated script list is missing: {', '.join(missing)}")
        if unexpected:
            report.errors.append(
                f"Generated script list has unexpected entries: {', '.join(unexpected)}"
            )

    return report

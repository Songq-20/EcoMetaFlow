"""Workflow validation helpers for run planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ecometa_flow.config import MODULE_NAMES
from ecometa_flow.envs import compare_requirements, load_envs, resolve_envs_path
from ecometa_flow.guards import validate_output_directory, validate_threads
from ecometa_flow.modules import MODULE_SCRIPTS
from ecometa_flow.parameters import ParameterError, load_effective_parameters
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
    force: bool
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
    output_dir_safe: bool = False
    output_guard_message: str = ""
    output_dir_exists: bool = False
    force_enabled: bool = False
    script_list_complete: bool = False
    dry_run_safe: bool = False
    execution_status: str = "Not started"
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
    force: bool,
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
        force=force,
        dry_run_safe=dry_run,
        force_enabled=force,
        execution_status=(
            "No external tools were executed in dry-run mode"
            if dry_run
            else "Real execution disabled in v0.5.0"
        ),
    )

    thread_errors, thread_warnings = validate_threads(threads)
    report.errors.extend(thread_errors)
    report.warnings.extend(thread_warnings)

    report.input_dir_exists = input_dir.is_dir()
    if not report.input_dir_exists:
        report.errors.append(f"Input folder does not exist: {input_dir}")

    guard = validate_output_directory(work_dir, input_dir, force)
    report.output_dir_safe = guard.safe
    report.output_guard_message = guard.message
    report.output_dir_exists = guard.output_exists
    if not guard.safe:
        report.errors.append(guard.message)

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

    try:
        report.params, report.params_loaded = load_effective_parameters(params_path)
    except ParameterError as exc:
        report.errors.append(str(exc))

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

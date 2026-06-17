"""Render workflow summaries for dry-run planning."""

from __future__ import annotations

from pathlib import Path

from ecometa_flow import __version__
from ecometa_flow.validation import WorkflowValidation


def _format_list(values: list[str]) -> str:
    """Return a compact human-readable list."""
    if not values:
        return "(none)"
    return ", ".join(values)


def _markdown_list(values: list[str]) -> list[str]:
    """Return Markdown bullet lines for a list."""
    if not values:
        return ["- (none)"]
    return [f"- {value}" for value in values]


def _escape_table_cell(value: object) -> str:
    """Escape Markdown table separators in a value."""
    return str(value).replace("|", "\\|")


def _samples_csv_status(report: WorkflowValidation) -> str:
    """Return the validation status for the optional samples.csv input."""
    if report.samples_path is None:
        return "not provided"
    if report.samples_valid:
        return "yes"
    return "no"


def _params_status(report: WorkflowValidation) -> str:
    """Return the validation status for the optional params YAML input."""
    if report.params_path is None:
        return "not provided"
    if report.params_loaded:
        return "yes"
    return "no"


def render_workflow_summary(report: WorkflowValidation) -> str:
    """Build the Markdown workflow summary document."""
    lines = [
        "# EcoMetaFlow Workflow Summary",
        "",
        f"- EcoMetaFlow version: {__version__}",
        f"- Module: {report.module}",
        f"- Input folder: {report.input_dir}",
        f"- samples.csv: {report.samples_path if report.samples_path else '(not provided)'}",
        f"- params.yaml: {report.params_path if report.params_path else '(not provided)'}",
        f"- Output directory: {report.work_dir}",
        f"- Threads: {report.threads}",
        f"- Dry-run: {'yes' if report.dry_run else 'no'}",
        f"- envs.yaml: {report.envs_path if report.envs_path else '(not found)'}",
        "",
        "## Validation",
        "",
        f"- Input folder exists: {'yes' if report.input_dir_exists else 'no'}",
        f"- Paired-end samples detected: {'yes' if report.samples_valid else 'no'}",
        f"- samples.csv valid: {_samples_csv_status(report)}",
        f"- params.yaml loaded: {_params_status(report)}",
        f"- Selected module supported: {'yes' if report.module_supported else 'no'}",
        f"- requirements.yaml loaded: {'yes' if report.requirements_loaded else 'no'}",
        f"- envs.yaml found: {'yes' if report.envs_found else 'no'}",
        f"- Output directory ready: {'yes' if report.output_dir_ready else 'no'}",
        f"- Generated script list complete: {'yes' if report.script_list_complete else 'no'}",
        f"- Dry-run will not execute external tools: {'yes' if report.dry_run_safe else 'no'}",
        "",
        "## Detected Samples",
        "",
        "| Sample ID | R1 | R2 |",
        "|---|---|---|",
    ]

    for sample in report.samples:
        lines.append(
            "| "
            f"{_escape_table_cell(sample.sample_id)} | "
            f"{_escape_table_cell(sample.r1)} | "
            f"{_escape_table_cell(sample.r2)} |"
        )
    if not report.samples:
        lines.append("| (none) |  |  |")

    lines.extend([
        "",
        "## Required Tools",
        "",
        *_markdown_list(report.requirements["tools"]),
        "",
        "## Available Tools",
        "",
        *_markdown_list(report.comparison["available_tools"]),
        "",
        "## Missing Tools",
        "",
        *_markdown_list(report.comparison["missing_tools"]),
        "",
        "## Required Databases",
        "",
        *_markdown_list(report.requirements["databases"]),
        "",
        "## Available Databases",
        "",
        *_markdown_list(report.comparison["available_databases"]),
        "",
        "## Missing Databases",
        "",
        *_markdown_list(report.comparison["missing_databases"]),
        "",
        "## Generated Scripts",
        "",
        *_markdown_list([str(path) for path in report.generated_scripts]),
        "",
        "## Dry-run Note",
        "",
        "No external tools were executed in dry-run mode. "
        "Generated shell scripts were written for inspection only.",
        "",
    ])

    if report.warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(_markdown_list(report.warnings))
        lines.append("")

    if report.errors:
        lines.extend(["## Errors", ""])
        lines.extend(_markdown_list(report.errors))
        lines.append("")

    return "\n".join(lines)


def write_workflow_summary(report: WorkflowValidation) -> Path:
    """Write workflow_summary.md inside the output work directory."""
    summary_path = report.work_dir / "workflow_summary.md"
    summary_path.write_text(render_workflow_summary(report), encoding="utf-8")
    return summary_path


def format_console_workflow_summary(
    report: WorkflowValidation,
    summary_path: Path | None,
) -> str:
    """Build the concise console summary for a planned workflow."""
    lines = [
        "=== Workflow summary ===",
        f"Module: {report.module}",
        f"Sample count: {len(report.samples)}",
        f"Missing tools: {_format_list(report.comparison['missing_tools'])}",
        f"Missing databases: {_format_list(report.comparison['missing_databases'])}",
        "Generated scripts:",
    ]

    if report.generated_scripts:
        for path in report.generated_scripts:
            lines.append(f"  - {path.name}")
    else:
        lines.append("  (none)")

    if summary_path:
        lines.append(f"workflow_summary.md: {summary_path}")

    if report.dry_run:
        lines.append("Dry-run: no external tools will be executed.")

    return "\n".join(lines)

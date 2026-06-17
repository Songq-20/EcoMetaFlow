"""Generate reader-facing workflow reports."""

from __future__ import annotations

from html import escape
from pathlib import Path

from ecometa_flow import __version__
from ecometa_flow.scanner import Sample
from ecometa_flow.validation import WorkflowValidation


PLANNED_STEPS: dict[str, str] = {
    "virus_prediction": (
        "raw reads -> Trimmomatic -> clean reads -> MEGAHIT -> contigs -> "
        "VirSorter2 / geNomad / VIBRANT / VirFinder -> viral contigs -> "
        "CheckV -> vOTU / taxonomy / mapping / abundance -> report"
    ),
    "mag_pipeline": (
        "raw reads -> Trimmomatic -> clean reads -> MEGAHIT -> contigs -> "
        "BASALT -> bins -> CheckM / CheckM2 -> dRep -> non-redundant MAGs -> "
        "GTDB-Tk taxonomy -> CoverM abundance -> report"
    ),
    "read_based_risk": (
        "raw reads -> Trimmomatic -> clean reads -> Kraken2 -> TaxonKit -> "
        "taxonomic profile -> pathogenic database comparison -> pathogenic taxa / "
        "reads -> risk abundance table -> report"
    ),
    "micro_risk": (
        "virus_prediction outputs + mag_pipeline outputs + read_based_risk outputs "
        "-> pathogenic virus/bacteria screening -> viral risk -> prokaryotic risk "
        "-> risk index -> optional phylogenetic validation -> integrated microbial "
        "risk report"
    ),
}

PLACEHOLDERS = [
    "viral contig summary: not generated yet",
    "MAG quality summary: not generated yet",
    "taxonomic abundance table: not generated yet",
    "microbial risk summary: not generated yet",
    "report plots: not generated yet",
]


def _value(value: object | None, missing: str = "not provided") -> str:
    """Format optional values for reports."""
    if value is None:
        return missing
    return str(value)


def _relpath(path: Path, root: Path) -> str:
    """Return a path relative to root when possible."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _markdown_bullets(values: list[str]) -> list[str]:
    """Render Markdown bullet lines."""
    if not values:
        return ["- (none)"]
    return [f"- {value}" for value in values]


def _markdown_sample_table(samples: list[Sample]) -> list[str]:
    """Render the sample table, or a readable no-samples note."""
    if not samples:
        return ["No samples were detected for this workflow plan."]

    lines = [
        "| SampleID | R1 | R2 |",
        "|---|---|---|",
    ]
    for sample in samples:
        lines.append(f"| {sample.sample_id} | {sample.r1} | {sample.r2} |")
    return lines


def _status_lines(report: WorkflowValidation) -> list[str]:
    """Build reader-friendly environment readiness bullets."""
    lines = [
        "Required tools:",
        *_markdown_bullets(report.requirements["tools"]),
        "",
        "Available tools from envs.yaml:",
        *_markdown_bullets(report.comparison["available_tools"]),
        "",
        "Tools found in PATH:",
    ]
    if report.tools_found_path:
        for tool, path in sorted(report.tools_found_path.items()):
            lines.append(f"- {tool}: {path}")
    else:
        lines.append("- (none)")
    lines.extend([
        "",
        "Missing tools after envs.yaml and PATH checks:",
        *_markdown_bullets(report.tools_missing_after_path),
        "",
        "Required databases:",
        *_markdown_bullets(report.requirements["databases"]),
        "",
        "Available databases:",
        *_markdown_bullets(report.comparison["available_databases"]),
        "",
        "Missing databases:",
        *_markdown_bullets(report.comparison["missing_databases"]),
    ])
    return lines


def _warning_lines(report: WorkflowValidation) -> list[str]:
    """Collect warnings and limitations for the reader-facing report."""
    lines: list[str] = []
    lines.extend(report.warnings)

    if not report.envs_found:
        lines.append("envs.yaml was not found; tools and databases may be incomplete.")
    if report.tools_missing_after_path:
        lines.append(
            "Some required tools are missing from both envs.yaml and PATH: "
            + ", ".join(report.tools_missing_after_path)
        )
    if report.comparison["missing_databases"]:
        lines.append(
            "Some required databases are missing from envs.yaml: "
            + ", ".join(report.comparison["missing_databases"])
        )
    if report.dry_run:
        lines.append("Dry-run mode was enabled; no external bioinformatics tools were executed.")
    lines.append("Real execution is disabled in this version.")
    lines.append("No biological result tables were generated.")
    return lines


def render_markdown_report(report: WorkflowValidation) -> str:
    """Render the reader-facing Markdown workflow report."""
    dry_run_text = "enabled" if report.dry_run else "disabled"
    planned_steps = PLANNED_STEPS.get(report.module, "planned workflow steps are not defined yet")

    lines = [
        "# EcoMetaFlow Report",
        "",
        "## 1. Overview",
        "",
        "This report summarizes an EcoMetaFlow workflow plan.",
        "EcoMetaFlow is a workflow runner, not a new bioinformatics algorithm.",
        f"Dry-run mode was {dry_run_text}.",
    ]
    if report.dry_run:
        lines.append("No external bioinformatics tools were executed.")
    lines.extend([
        "",
        "## 2. Run information",
        "",
        f"- module: {report.module}",
        f"- input directory: {report.input_dir}",
        f"- samples.csv: {_value(report.samples_path)}",
        f"- output directory: {report.work_dir}",
        f"- envs.yaml: {_value(report.envs_path, 'not found')}",
        f"- params.yaml: {_value(report.params_path)}",
        f"- threads: {report.threads}",
        f"- dry-run: {'yes' if report.dry_run else 'no'}",
        f"- force: {'yes' if report.force_enabled else 'no'}",
        f"- EcoMetaFlow version: {__version__}",
        "",
        "## 3. Sample information",
        "",
        *_markdown_sample_table(report.samples),
        "",
        "## 4. Environment readiness",
        "",
        "This section summarizes whether the workflow appears ready for future real execution.",
        "",
        *_status_lines(report),
        "",
        "## 5. Planned workflow",
        "",
        planned_steps,
        "",
        "## 6. Generated workflow scripts",
        "",
        "These scripts contain generated or planned commands for review.",
    ])

    if report.generated_scripts:
        for script in report.generated_scripts:
            lines.append(f"- {script.name}: `{_relpath(script, report.work_dir)}`")
    else:
        lines.append("- (none)")

    lines.extend([
        "",
        "## 7. Current outputs and future result placeholders",
        "",
        "These sections will be populated in future versions after real workflow execution and result parsing are implemented.",
        "",
        *_markdown_bullets(PLACEHOLDERS),
        "",
        "## 8. Warnings and limitations",
        "",
        *_markdown_bullets(_warning_lines(report)),
        "",
        "## 9. Reproducibility notes",
        "",
        f"- command-line mode: {'dry-run' if report.dry_run else 'execution requested'}",
        f"- generated script directory: {report.work_dir / 'scripts'}",
        f"- envs.yaml: {_value(report.envs_path, 'not found')}",
        f"- params.yaml: {_value(report.params_path)}",
        f"- samples.csv: {_value(report.samples_path)}",
        f"- dry-run: {'yes' if report.dry_run else 'no'}",
        "- workflow_summary.md contains compact technical metadata for debugging and tracing.",
        "",
    ])
    return "\n".join(lines)


def _html_list(values: list[str]) -> str:
    """Render a simple HTML unordered list."""
    if not values:
        values = ["(none)"]
    items = "\n".join(f"<li>{escape(value)}</li>" for value in values)
    return f"<ul>\n{items}\n</ul>"


def _html_sample_table(samples: list[Sample]) -> str:
    """Render the sample table in HTML."""
    if not samples:
        return "<p>No samples were detected for this workflow plan.</p>"
    rows = []
    for sample in samples:
        rows.append(
            "<tr>"
            f"<td>{escape(sample.sample_id)}</td>"
            f"<td>{escape(str(sample.r1))}</td>"
            f"<td>{escape(str(sample.r2))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>SampleID</th><th>R1</th><th>R2</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _html_key_values(items: list[tuple[str, str]]) -> str:
    """Render key-value rows as a compact table."""
    rows = [
        f"<tr><th>{escape(key)}</th><td>{escape(value)}</td></tr>"
        for key, value in items
    ]
    return f"<table>{''.join(rows)}</table>"


def render_html_report(report: WorkflowValidation) -> str:
    """Render the reader-facing static HTML workflow report."""
    planned_steps = PLANNED_STEPS.get(report.module, "planned workflow steps are not defined yet")
    scripts = [
        f"{script.name}: {_relpath(script, report.work_dir)}"
        for script in report.generated_scripts
    ]
    path_tools = [
        f"{tool}: {path}" for tool, path in sorted(report.tools_found_path.items())
    ]
    run_info = [
        ("module", report.module),
        ("input directory", str(report.input_dir)),
        ("samples.csv", _value(report.samples_path)),
        ("output directory", str(report.work_dir)),
        ("envs.yaml", _value(report.envs_path, "not found")),
        ("params.yaml", _value(report.params_path)),
        ("threads", str(report.threads)),
        ("dry-run", "yes" if report.dry_run else "no"),
        ("force", "yes" if report.force_enabled else "no"),
        ("EcoMetaFlow version", __version__),
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>EcoMetaFlow Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.55; color: #1f2933; max-width: 980px; margin: 2rem auto; padding: 0 1rem; }}
    h1, h2 {{ color: #102a43; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #bcccdc; padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }}
    th {{ background: #f0f4f8; }}
    code {{ background: #f0f4f8; padding: 0.1rem 0.25rem; }}
    .note {{ background: #f8fafc; border-left: 4px solid #486581; padding: 0.75rem 1rem; }}
  </style>
</head>
<body>
  <h1>EcoMetaFlow Report</h1>

  <h2>1. Overview</h2>
  <p>This report summarizes an EcoMetaFlow workflow plan. EcoMetaFlow is a workflow runner, not a new bioinformatics algorithm.</p>
  <p>Dry-run mode was {"enabled" if report.dry_run else "disabled"}.</p>
  <p class="note">{"No external bioinformatics tools were executed." if report.dry_run else "Real execution is disabled in this version."}</p>

  <h2>2. Run information</h2>
  {_html_key_values(run_info)}

  <h2>3. Sample information</h2>
  {_html_sample_table(report.samples)}

  <h2>4. Environment readiness</h2>
  <p>This section summarizes whether the workflow appears ready for future real execution.</p>
  <h3>Required tools</h3>{_html_list(report.requirements["tools"])}
  <h3>Available tools from envs.yaml</h3>{_html_list(report.comparison["available_tools"])}
  <h3>Tools found in PATH</h3>{_html_list(path_tools)}
  <h3>Missing tools after envs.yaml and PATH checks</h3>{_html_list(report.tools_missing_after_path)}
  <h3>Required databases</h3>{_html_list(report.requirements["databases"])}
  <h3>Available databases</h3>{_html_list(report.comparison["available_databases"])}
  <h3>Missing databases</h3>{_html_list(report.comparison["missing_databases"])}

  <h2>5. Planned workflow</h2>
  <p>{escape(planned_steps)}</p>

  <h2>6. Generated workflow scripts</h2>
  <p>These scripts contain generated or planned commands for review.</p>
  {_html_list(scripts)}

  <h2>7. Current outputs and future result placeholders</h2>
  <p>These sections will be populated in future versions after real workflow execution and result parsing are implemented.</p>
  {_html_list(PLACEHOLDERS)}

  <h2>8. Warnings and limitations</h2>
  {_html_list(_warning_lines(report))}

  <h2>9. Reproducibility notes</h2>
  {_html_list([
      "command-line mode: " + ("dry-run" if report.dry_run else "execution requested"),
      "generated script directory: " + str(report.work_dir / "scripts"),
      "envs.yaml: " + _value(report.envs_path, "not found"),
      "params.yaml: " + _value(report.params_path),
      "samples.csv: " + _value(report.samples_path),
      "dry-run: " + ("yes" if report.dry_run else "no"),
      "workflow_summary.md contains compact technical metadata for debugging and tracing.",
  ])}
</body>
</html>
"""


def write_reports(report: WorkflowValidation) -> tuple[Path, Path]:
    """Write report/report.md and report/report.html under the work directory."""
    report_dir = report.work_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = report_dir / "report.md"
    html_path = report_dir / "report.html"
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
    html_path.write_text(render_html_report(report), encoding="utf-8")
    return markdown_path, html_path

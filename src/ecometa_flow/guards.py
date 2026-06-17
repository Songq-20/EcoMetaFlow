"""Safety checks for workflow output handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class OutputGuardResult:
    """Result of output directory safety checks."""

    safe: bool
    message: str
    output_exists: bool
    force: bool


def _repo_root() -> Path:
    """Return the project repository root for local safety checks."""
    return Path(__file__).resolve().parents[2]


def validate_output_directory(
    output_dir: Path,
    input_dir: Path,
    force: bool,
) -> OutputGuardResult:
    """Refuse unsafe or surprising output directories."""
    output = output_dir.resolve()
    input_path = input_dir.resolve()
    home = Path.home().resolve()
    repo_root = _repo_root()
    output_exists = output.exists()

    unsafe_reasons: list[str] = []
    if output == Path("/"):
        unsafe_reasons.append("output directory cannot be the filesystem root")
    if output == home:
        unsafe_reasons.append("output directory cannot be your home directory")
    if output == repo_root:
        unsafe_reasons.append("output directory cannot be the project repository root")
    if output == input_path:
        unsafe_reasons.append("output directory cannot be the input directory")

    if unsafe_reasons:
        return OutputGuardResult(
            safe=False,
            message="; ".join(unsafe_reasons),
            output_exists=output_exists,
            force=force,
        )

    if output_exists and not output.is_dir():
        return OutputGuardResult(
            safe=False,
            message=f"output path exists but is not a directory: {output}",
            output_exists=True,
            force=force,
        )

    if output_exists and not force:
        return OutputGuardResult(
            safe=False,
            message=(
                f"output directory already exists: {output}. "
                "Use --force to regenerate dry-run scripts and workflow_summary.md."
            ),
            output_exists=True,
            force=force,
        )

    if output_exists:
        message = "output directory exists and --force allows regeneration"
    else:
        message = "output directory is safe to create"

    return OutputGuardResult(
        safe=True,
        message=message,
        output_exists=output_exists,
        force=force,
    )


def validate_threads(threads: int) -> tuple[list[str], list[str]]:
    """Return errors and warnings for the requested thread count."""
    errors: list[str] = []
    warnings: list[str] = []

    if threads < 1:
        errors.append("threads must be >= 1")
    elif threads > 128:
        warnings.append(
            f"threads is set to {threads}; values above 128 may be excessive."
        )

    return errors, warnings

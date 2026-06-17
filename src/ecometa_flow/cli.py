"""EcoMetaFlow command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ecometa_flow import __version__
from ecometa_flow.config import DEFAULT_THREADS, MODULE_NAMES
from ecometa_flow.envs import (
    compare_requirements,
    format_check_report,
    load_envs,
    resolve_envs_path,
)
from ecometa_flow.installer import run_install
from ecometa_flow.requirements import get_module_requirements
from ecometa_flow.runner import create_work_directories, run_scripts, write_scripts
from ecometa_flow.summary import (
    format_console_workflow_summary,
    write_workflow_summary,
)
from ecometa_flow.validation import validate_generated_scripts, validate_workflow


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecometa-flow",
        description="EcoMetaFlow: environmental metagenomics workflow runner",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"EcoMetaFlow {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- run ---
    run_parser = subparsers.add_parser("run", help="Run a workflow module")
    run_parser.add_argument(
        "-m", "--module",
        required=True,
        choices=MODULE_NAMES,
        help="Workflow module to run",
    )
    run_parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input folder containing paired-end FASTQ files",
    )
    run_parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output work directory",
    )
    run_parser.add_argument(
        "--samples",
        help="Optional samples.csv for non-standard file names",
    )
    run_parser.add_argument(
        "--envs",
        help="Path to envs.yaml (overrides auto-discovery)",
    )
    run_parser.add_argument(
        "--params",
        help="Optional YAML file with workflow parameters",
    )
    run_parser.add_argument(
        "-t", "--threads",
        type=int,
        default=DEFAULT_THREADS,
        help=f"Number of threads (default: {DEFAULT_THREADS})",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned commands without executing them",
    )
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="Allow regenerating dry-run outputs in an existing output directory",
    )

    # --- check ---
    check_parser = subparsers.add_parser(
        "check", help="Check tools and databases for a module"
    )
    check_parser.add_argument(
        "--module",
        required=True,
        choices=MODULE_NAMES,
        help="Module to check",
    )
    check_parser.add_argument(
        "--envs",
        help="Path to envs.yaml (overrides auto-discovery)",
    )

    # --- install ---
    install_parser = subparsers.add_parser(
        "install", help="Plan installation of tools and databases in dry-run mode"
    )
    install_group = install_parser.add_mutually_exclusive_group(required=True)
    install_group.add_argument(
        "--module",
        choices=MODULE_NAMES,
        help="Install requirements for a single module",
    )
    install_group.add_argument(
        "--all",
        action="store_true",
        help="Install requirements for all modules",
    )
    install_parser.add_argument(
        "--envs",
        help="Path to envs.yaml (overrides auto-discovery)",
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show install plan without making changes (default in v0.5.0)",
    )
    install_parser.add_argument(
        "--write-script",
        help="Write a review-only shell script with suggested conda commands",
    )
    install_parser.add_argument(
        "--write-envs",
        help="Write an envs.yaml template for review",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting generated bootstrap files",
    )

    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """Handle the 'run' subcommand."""
    input_dir = Path(args.input).resolve()
    work_dir = Path(args.output).resolve()
    module = args.module
    samples_path = Path(args.samples).resolve() if args.samples else None
    params_path = Path(args.params).resolve() if args.params else None

    if not args.dry_run:
        print(
            "Error: Real execution is not enabled in this version. "
            "Please use --dry-run.",
            file=sys.stderr,
        )
        return 1

    validation = validate_workflow(
        module=module,
        input_dir=input_dir,
        work_dir=work_dir,
        samples_path=samples_path,
        params_path=params_path,
        envs_cli=args.envs,
        threads=args.threads,
        dry_run=args.dry_run,
        force=args.force,
    )

    if not validation.ok:
        for error in validation.errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Detected {len(validation.samples)} sample(s):")
    for sample in validation.samples:
        print(f"  {sample.sample_id}: {sample.r1.name} + {sample.r2.name}")

    print()
    print(
        format_check_report(
            module,
            validation.requirements,
            validation.comparison,
            validation.envs_path,
        )
    )

    if (
        validation.comparison["missing_tools"]
        or validation.comparison["missing_databases"]
    ):
        print(
            "\nWarning: Some required tools or databases are missing. "
            "Run 'ecometa-flow install --module ... --dry-run' for guidance.",
            file=sys.stderr,
        )

    print(f"\nCreating work directory: {work_dir}")
    create_work_directories(module, work_dir)

    script_paths = write_scripts(
        module, work_dir, validation.samples, validation.envs, args.threads
    )
    validate_generated_scripts(validation, script_paths)
    if not validation.ok:
        for error in validation.errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Wrote {len(script_paths)} script(s) to {work_dir / 'scripts'}")

    summary_path = None
    if args.dry_run:
        summary_path = write_workflow_summary(validation)
        print()
        print(format_console_workflow_summary(validation, summary_path))

    if args.dry_run:
        print("\n=== Dry-run: planned commands ===")
    else:
        print("\n=== Executing scripts ===")

    run_scripts(script_paths, dry_run=args.dry_run)

    if args.dry_run:
        print("\nDry-run complete. No commands were executed.")

    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Handle the 'check' subcommand."""
    module = args.module
    required = get_module_requirements(module)
    envs_path = resolve_envs_path(args.envs)
    envs = load_envs(envs_path)
    comparison = compare_requirements(
        required["tools"], required["databases"], envs
    )

    print(format_check_report(module, required, comparison, envs_path))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    """Handle the 'install' subcommand."""
    try:
        report = run_install(
            module=args.module,
            install_all=args.all,
            envs_cli=args.envs,
            dry_run=args.dry_run,
            write_script=Path(args.write_script).resolve()
            if args.write_script
            else None,
            write_envs=Path(args.write_envs).resolve() if args.write_envs else None,
            force=args.force,
        )
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(report)
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return cmd_run(args)
    if args.command == "check":
        return cmd_check(args)
    if args.command == "install":
        return cmd_install(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

# Changelog

All notable changes to EcoMetaFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-06-17

### Added

- PATH-aware tool detection for install planning with `shutil.which()`
- Install reports that distinguish tools configured in `envs.yaml`, tools found
  in PATH, tools still missing, and databases requiring explicit paths
- `install --write-script PATH` for review-only conda bootstrap scripts
- `install --write-envs PATH` for review-only `envs.yaml` templates
- `install --force` for overwriting generated bootstrap files only
- Tests for PATH detection, bootstrap file generation, overwrite protection,
  database safety, and non-execution of conda commands

### Changed

- CLI version bumped to `0.5.0`
- Generated script headers now identify the v0.5.0 dry-run workflow plan
- Install reports now explicitly say no installation or database download was
  performed

## [0.4.0] - 2026-06-17

### Added

- Output directory execution guards for unsafe paths, existing output
  directories, input/output overlap, and `--force` regeneration
- Thread count validation with errors for values below 1 and warnings above 128
- Safe refusal of non-dry-run mode with a clear message that real execution is
  disabled in v0.4.0
- Built-in workflow parameter defaults, recursive params YAML merging, and
  params validation
- Effective parameters and output guard details in `workflow_summary.md`
- Tests covering output guards, `--force`, params errors, effective parameter
  reporting, and non-dry-run refusal

### Changed

- CLI version bumped to `0.4.0`
- Generated script headers now identify the v0.4.0 dry-run workflow plan

## [0.3.0] - 2026-06-17

### Added

- Workflow validation for input folders, sample detection, optional
  `samples.csv`, module support, built-in requirements, `envs.yaml`, required
  tools/databases, output directory creation, generated scripts, and dry-run
  safety
- Optional `--params` support for recording and loading workflow parameter YAML
  files during `run --dry-run`
- `workflow_summary.md` generation after `run --dry-run`
- Readable console workflow summary with module, sample count, missing
  requirements, generated scripts, and summary path
- Tests for validation, missing inputs, missing `envs.yaml`, summary creation,
  and dry-run non-execution

### Changed

- CLI version bumped to `0.3.0`
- Generated script headers now identify the v0.3.0 dry-run workflow plan

## [0.2.0] - 2026-06-08

### Added

- Realistic dry-run command generation for `virus_prediction`, `mag_pipeline`,
  `read_based_risk`, and `micro_risk`
- Dry-run installation planning with copyable `conda create -p ...` commands
- Tests covering workflow command rendering and installer output

### Changed

- `00_check_environment.sh` now reports resolved tool commands and database paths
- CLI version bumped to `0.2.0`

## [0.1.0] - 2026-06-08

### Added

- Python CLI skeleton with `run`, `check`, and `install` subcommands
- Automatic paired-end FASTQ sample detection (`_R1/_R2`, `_1/_2`, `.R1/.R2`)
- Optional `samples.csv` input for non-standard file names
- Four workflow modules: `virus_prediction`, `mag_pipeline`, `read_based_risk`, `micro_risk`
- Built-in `requirements.yaml` and `install.yaml`
- `envs.yaml` discovery with CLI, environment variable, and default path lookup
- Work directory and shell script generation with `--dry-run` support
- Example data under `examples/`
- Unit tests for scanner, samples, envs, and requirements

### Limitations

- Does not execute real bioinformatics tools
- `install` is mock/dry-run only (no conda environments or database downloads)

[0.1.0]: https://github.com/songqi/EcoMetaFlow/releases/tag/v0.1.0

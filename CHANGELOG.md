# Changelog

All notable changes to EcoMetaFlow are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

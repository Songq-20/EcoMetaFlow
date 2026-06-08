# Cursor Prompt for EcoMetaFlow v0.1.0

Copy the prompt below into Cursor Agent in an empty project folder.

---

You are a senior Python developer helping me build **EcoMetaFlow**, a beginner-friendly bioinformatics workflow runner for environmental metagenomic, metaviromic, and microbial risk analysis.

## Project concept

EcoMetaFlow is not a new bioinformatics algorithm. It is a workflow runner that will later call existing tools such as Trimmomatic, MEGAHIT, VirSorter2, geNomad, VIBRANT, CheckV, BASALT, CheckM, dRep, GTDB-Tk, Kraken2, TaxonKit, Bowtie2, Samtools, and CoverM.

For v0.1.0, do **not** run real bioinformatics tools. Build a clean, small, testable CLI skeleton.

## Main goal for v0.1.0

Create a Python CLI project that can:

1. Accept an input folder containing paired-end `.fq.gz` / `.fastq.gz` files.
2. Automatically scan and detect paired-end samples.
3. Support optional `--samples samples.csv` for non-standard file names.
4. Support four module names:
   - `virus_prediction`
   - `mag_pipeline`
   - `read_based_risk`
   - `micro_risk`
5. Use built-in `requirements.yaml` to define which tools/databases each module requires.
6. Read an optional `envs.yaml` to know where tools/databases are installed.
7. Compare module requirements with `envs.yaml` and report missing tools/databases.
8. Support `install --module MODULE` and `install --all`, but only as dry-run/mock installation in v0.1.0.
9. Create standard work directories.
10. Generate planned shell commands for each module.
11. Support `--dry-run` so commands are printed but not executed.
12. Include a user-facing README.md.

## Important design decisions

### Input design

Default user input is a folder:

```bash
ecometa-flow run -m virus_prediction -i raw_reads -o work_virus -t 16 --dry-run
```

The program should scan:

```text
*.fq.gz
*.fastq.gz
*.fq
*.fastq
```

Support these paired-end patterns in v0.1.0:

```text
Sample_R1.fq.gz / Sample_R2.fq.gz
Sample_1.fq.gz  / Sample_2.fq.gz
Sample.R1.fq.gz / Sample.R2.fq.gz
```

If auto-detection fails, print a clear error and suggest using `--samples samples.csv`.

### envs.yaml design

`envs.yaml` is necessary for HPC/shared deployment, but local beginner users should not be forced to write it manually.

For v0.1.0:

- Provide an example `examples/envs.yaml`.
- Provide built-in logic to read it.
- Provide `install` command as dry-run/mock logic.
- Do not really create conda environments.
- Do not really download large databases.

Lookup priority for envs.yaml:

1. `--envs` command-line argument
2. `$ECOMETA_ENVS` environment variable
3. `./envs.yaml`
4. `~/.ecometa-flow/envs.yaml`
5. `$ECOMETA_HOME/config/envs.yaml`
6. If still missing, continue but report required tools/databases as missing.

Example envs.yaml format:

```yaml
tools:
  trimmomatic:
    mode: conda
    env: /data/software/ecometa-flow/envs/trimmomatic
    command: trimmomatic

  megahit:
    mode: command
    command: megahit

databases:
  checkv_db: /data/database/checkv-db
  kraken2_db: /data/database/kraken2-db
```

Support `mode: command` and `mode: conda` only for now.

### requirements.yaml design

Create built-in `src/ecometa_flow/data/requirements.yaml`:

```yaml
modules:
  virus_prediction:
    tools:
      - trimmomatic
      - megahit
      - virsorter2
      - genomad
      - vibrant
      - checkv
      - bowtie2
      - samtools
    databases:
      - checkv_db

  mag_pipeline:
    tools:
      - trimmomatic
      - megahit
      - basalt
      - checkm
      - drep
      - gtdbtk
      - coverm
    databases:
      - gtdbtk_db

  read_based_risk:
    tools:
      - trimmomatic
      - kraken2
      - taxonkit
    databases:
      - kraken2_db
      - pathogen_db

  micro_risk:
    tools:
      - trimmomatic
      - kraken2
      - taxonkit
      - bowtie2
      - samtools
    databases:
      - kraken2_db
      - pathogen_db
      - checkv_db
```

### install.yaml design

Create built-in `src/ecometa_flow/data/install.yaml` with mock installation recipes. It should exist for future extension, but v0.1.0 should not execute real installation.

## Required CLI commands

Use Python standard library `argparse`, not Click/Typer.

### 1. run

Example:

```bash
python -m ecometa_flow.cli run \
  -m virus_prediction \
  -i examples/raw_reads \
  -o work_virus \
  --envs examples/envs.yaml \
  -t 16 \
  --dry-run
```

Expected behavior:

- scan input reads folder
- detect samples
- load requirements
- load envs if available
- report missing tools/databases
- create work directory structure
- generate planned shell commands
- print commands if `--dry-run`

### 2. check

Example:

```bash
python -m ecometa_flow.cli check \
  --module virus_prediction \
  --envs examples/envs.yaml
```

Expected behavior:

- list required tools/databases
- list available tools/databases from envs.yaml
- list missing tools/databases

### 3. install

Examples:

```bash
python -m ecometa_flow.cli install --module virus_prediction --dry-run
python -m ecometa_flow.cli install --all --dry-run
```

Expected behavior:

- read requirements
- compare with envs.yaml if provided or found
- print what would be installed
- do not really install anything

## Expected project structure

Create this structure:

```text
EcoMetaFlow/
├── README.md
├── pyproject.toml
├── requirements.txt
├── examples/
│   ├── raw_reads/
│   │   ├── S1_R1.fq.gz
│   │   ├── S1_R2.fq.gz
│   │   ├── S2_R1.fq.gz
│   │   └── S2_R2.fq.gz
│   ├── samples.csv
│   ├── envs.yaml
│   └── params.yaml
├── src/
│   └── ecometa_flow/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── requirements.py
│       ├── envs.py
│       ├── samples.py
│       ├── scanner.py
│       ├── modules.py
│       ├── commands.py
│       ├── runner.py
│       └── installer.py
├── src/ecometa_flow/data/
│   ├── requirements.yaml
│   └── install.yaml
└── tests/
    ├── test_scanner.py
    ├── test_samples.py
    ├── test_envs.py
    └── test_requirements.py
```

## Generated work directory structure

When running a module, create:

```text
work_virus/
├── config/
├── data/
├── logs/
├── results/
│   ├── clean_reads/
│   ├── assembly/
│   ├── virus_prediction/
│   ├── mapping/
│   └── abundance/
├── scripts/
│   ├── 00_check_environment.sh
│   ├── 01_trimming.sh
│   ├── 02_assembly.sh
│   └── 03_virus_prediction.sh
└── tmp/
```

For other modules, create reasonable analogous directories.

## Coding restrictions

Strictly follow these restrictions:

1. Do not over-engineer.
2. Do not add Snakemake, Nextflow, Docker, Apptainer, or web UI.
3. Do not run real external bioinformatics tools.
4. Do not download real databases.
5. Do not create conda environments in v0.1.0.
6. Use Python standard library + PyYAML only.
7. Use `pathlib` for all paths.
8. Use `argparse` for CLI.
9. Keep functions small and beginner-readable.
10. Add helpful comments.
11. Print human-readable error messages.
12. Tests should not depend on real bioinformatics tools.
13. Do not create excessive abstractions.
14. The project must run locally after installation.

## After finishing, report

After you create the project, tell me:

1. Which files you created.
2. How to install the package in editable mode.
3. How to run the example `run` command.
4. How to run the `check` command.
5. How to run the `install --dry-run` command.
6. What limitations remain in v0.1.0.

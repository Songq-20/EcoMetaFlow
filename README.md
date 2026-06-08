# EcoMetaFlow

EcoMetaFlow is a beginner-friendly bioinformatics workflow runner for environmental metagenomic, metaviromic, and microbial risk analysis.

It is designed to help users organize and run common environmental omics workflows with fewer manual configuration steps.

> Current version: v0.2.0  
> Status: dry-run workflow planner with realistic shell command generation. It does not execute real bioinformatics tools in this version.

---

## What EcoMetaFlow is

EcoMetaFlow is not a new bioinformatics algorithm. It is a workflow orchestration tool that will later call existing tools such as:

- Trimmomatic
- MEGAHIT
- VirSorter2
- geNomad
- VIBRANT
- CheckV
- BASALT
- CheckM / CheckM2
- dRep
- GTDB-Tk
- Kraken2
- TaxonKit
- Bowtie2
- Samtools
- CoverM

The long-term goal is to support environmental metagenomic, metaviromic, MAG, and microbial risk workflows.

---

## Supported modules

EcoMetaFlow currently defines four module names:

| Module | Purpose |
|---|---|
| `virus_prediction` | Viral contig prediction, vOTU construction, taxonomy, abundance. |
| `mag_pipeline` | Assembly, binning, MAG quality control, dereplication, taxonomy, abundance. |
| `read_based_risk` | Read-based microbial risk screening using taxonomic classification. |
| `micro_risk` | Integrated microbial risk analysis based on viral, MAG, and read-based results. |

In v0.2.0, these modules generate realistic dry-run shell commands and directory structures. They still do not run real external tools.

---

## Installation

Clone the repository and install it in editable mode:

```bash
git clone <your-repository-url>
cd EcoMetaFlow
pip install -e .
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

v0.2.0 only requires:

```text
PyYAML
```

---

## Quick start

Prepare a folder containing paired-end FASTQ files:

```text
raw_reads/
├── S1_R1.fq.gz
├── S1_R2.fq.gz
├── S2_R1.fq.gz
└── S2_R2.fq.gz
```

Run EcoMetaFlow in dry-run mode:

```bash
ecometa-flow run \
  -m virus_prediction \
  -i examples/raw_reads \
  -o work_virus \
  --envs examples/envs.yaml \
  -t 16 \
  --dry-run
```

Dry-run mode prints the planned commands but does not execute them.

In v0.2.0, the generated scripts now include realistic commands for:

- read trimming
- assembly
- viral prediction and abundance estimation
- MAG binning, QC, taxonomy, and abundance estimation
- read-based taxonomic screening and pathogen summaries
- integrated microbial risk dry-run planning

---

## Input file naming rules

EcoMetaFlow scans the input folder and detects paired-end reads automatically.

v0.2.0 supports these common patterns:

```text
Sample_R1.fq.gz / Sample_R2.fq.gz
Sample_1.fq.gz  / Sample_2.fq.gz
Sample.R1.fq.gz / Sample.R2.fq.gz
```

Supported file extensions:

```text
.fq.gz
.fastq.gz
.fq
.fastq
```

If your file names are not recognized, use a sample sheet.

---

## Optional sample sheet

For non-standard file names, provide `--samples samples.csv`.

Example:

```csv
SampleID,R1,R2,Group,DataType
S1,data/S1_R1.fq.gz,data/S1_R2.fq.gz,RW,metagenome
S2,data/S2_R1.fq.gz,data/S2_R2.fq.gz,WW,metavirome
```

Required columns:

```text
SampleID,R1,R2
```

Run with a sample sheet:

```bash
ecometa-flow run \
  -m virus_prediction \
  -i examples/raw_reads \
  --samples examples/samples.csv \
  -o work_virus \
  --dry-run
```

---

## Environment configuration

EcoMetaFlow supports both local installation and HPC/shared deployment.

### For local beginner users

In future versions, EcoMetaFlow will support automatic installation:

```bash
ecometa-flow install --module virus_prediction
```

or:

```bash
ecometa-flow install --all
```

In v0.2.0, installation is still dry-run only. It reports the `conda create -p ...` commands that would be used and suggests matching `envs.yaml` entries.

### For HPC/shared users

If your lab or HPC administrator already installed the required tools, provide an `envs.yaml` file:

```bash
ecometa-flow run \
  -m virus_prediction \
  -i examples/raw_reads \
  -o work_virus \
  --envs examples/envs.yaml \
  --dry-run
```

You can also set an environment variable:

```bash
export ECOMETA_ENVS=/path/to/envs.yaml
```

Then run:

```bash
ecometa-flow run -m virus_prediction -i examples/raw_reads -o work_virus --dry-run
```

---

## envs.yaml format

`envs.yaml` tells EcoMetaFlow where tools and databases are located.

Example:

```yaml
tools:
  trimmomatic:
    mode: conda
    env: /data/software/ecometa-flow/envs/trimmomatic
    command: trimmomatic

  megahit:
    mode: command
    command: megahit

  checkv:
    mode: conda
    env: /data/software/ecometa-flow/envs/checkv
    command: checkv

databases:
  checkv_db: /data/database/checkv-db
  kraken2_db: /data/database/kraken2-db
  gtdbtk_db: /data/database/gtdbtk-db
```

Currently supported tool modes:

| Mode | Meaning |
|---|---|
| `command` | The command is already available in PATH. |
| `conda` | The command should be run using `conda run -p <env> <command>`. |

Future versions may support `module`, `apptainer`, `singularity`, and absolute executable paths.

---

## Check module requirements

To check what a module needs:

```bash
ecometa-flow check --module virus_prediction --envs examples/envs.yaml
```

This prints:

- required tools
- required databases
- available tools/databases from `envs.yaml`
- missing tools/databases

---

## Mock installation

Install dependencies for one module:

```bash
ecometa-flow install --module virus_prediction --dry-run
```

Install everything:

```bash
ecometa-flow install --all --dry-run
```

`--all` may be very large in future versions because databases can be huge. Most users should start with module-level installation.

In v0.2.0, `install` still does not download tools or databases. It only reports what would be installed.

---

## Output directory

A dry-run for `virus_prediction` creates a work directory like this:

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

---

## Running tests

```bash
pip install pytest
pytest tests/
```

---

## Current limitations

v0.2.0 is still a safe dry-run release.

It does not:

- execute real Trimmomatic / MEGAHIT / VirSorter2 / CheckV commands
- create real conda environments
- download large databases
- run Snakemake or Nextflow
- generate final biological reports
- calculate real risk indexes
- support all possible FASTQ naming patterns

The purpose of v0.2.0 is to provide realistic, inspectable workflow scripts while keeping the CLI, environment checks, and dry-run safety model beginner-friendly.

---

## Roadmap

### v0.3.0

Add optional report summarization and richer workflow validation.

### v0.4.0

Add execution guards and more configurable module-level parameters.

### v0.5.0

Add safer semi-automated environment bootstrapping.

### v0.6.0

Generate initial Markdown/HTML reports.

### v0.7.0+

Add risk index calculation, phylogenetic validation, and advanced visualization.

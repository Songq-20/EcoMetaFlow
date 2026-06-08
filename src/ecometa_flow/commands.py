"""Generate planned shell commands for each workflow module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ecometa_flow.envs import resolve_tool_command
from ecometa_flow.scanner import Sample


def _tool(envs: dict[str, Any], name: str) -> str:
    """Resolve a tool name to a shell command prefix (or placeholder)."""
    tools = envs.get("tools", {})
    if name in tools:
        return resolve_tool_command(name, tools[name])
    return f"<{name}>"


def _db(envs: dict[str, Any], name: str) -> str:
    """Resolve a database name to a path (or placeholder)."""
    databases = envs.get("databases", {})
    if name in databases:
        return str(databases[name])
    return f"<{name}_not_configured>"


def generate_script_contents(
    module: str,
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    """Return the shell script body for a given step."""
    header = (
        "#!/usr/bin/env bash\n"
        f"# EcoMetaFlow v0.1.0 — planned command (not executed in skeleton mode)\n"
        f"# Module: {module}\n"
        f"# Script: {script_name}\n"
        "set -euo pipefail\n\n"
    )

    if script_name == "00_check_environment.sh":
        body = (
            'echo "Checking required tools and databases..."\n'
            "# Missing tools/databases should be installed before a real run.\n"
        )
        return header + body

    if module == "virus_prediction":
        return header + _virus_prediction_script(
            script_name, samples, work_dir, envs, threads
        )
    if module == "mag_pipeline":
        return header + _mag_pipeline_script(
            script_name, samples, work_dir, envs, threads
        )
    if module == "read_based_risk":
        return header + _read_based_risk_script(
            script_name, samples, work_dir, envs, threads
        )
    if module == "micro_risk":
        return header + _micro_risk_script(
            script_name, samples, work_dir, envs, threads
        )

    return header + f'echo "No commands defined for {script_name}"\n'


def _virus_prediction_script(
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    trim = _tool(envs, "trimmomatic")
    megahit = _tool(envs, "megahit")
    virsorter = _tool(envs, "virsorter2")
    checkv = _tool(envs, "checkv")
    bowtie2 = _tool(envs, "bowtie2")
    samtools = _tool(envs, "samtools")
    checkv_db = _db(envs, "checkv_db")

    lines: list[str] = []

    if script_name == "01_trimming.sh":
        for sample in samples:
            out_r1 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R1.fastq.gz"
            out_r2 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R2.fastq.gz"
            lines.append(
                f'{trim} PE -threads {threads} '
                f'"{sample.r1}" "{sample.r2}" '
                f'"{out_r1}" /dev/null "{out_r2}" /dev/null '
                f'ILLUMINACLIP:TruSeq3-PE.fa:2:30:10 LEADING:3 TRAILING:3 '
                f'SLIDINGWINDOW:4:15 MINLEN:36'
            )
    elif script_name == "02_assembly.sh":
        for sample in samples:
            clean_r1 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R1.fastq.gz"
            clean_r2 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R2.fastq.gz"
            out_dir = work_dir / "results" / "assembly" / sample.sample_id
            lines.append(
                f'{megahit} -1 "{clean_r1}" -2 "{clean_r2}" '
                f'-o "{out_dir}" -t {threads}'
            )
    elif script_name == "03_virus_prediction.sh":
        for sample in samples:
            contigs = work_dir / "results" / "assembly" / sample.sample_id / "final.contigs.fa"
            out_dir = work_dir / "results" / "virus_prediction" / sample.sample_id
            lines.append(f'{virsorter} --input "{contigs}" --output "{out_dir}"')
            lines.append(
                f'{checkv} end_to_end "{out_dir}/final-viral-combined.fa" '
                f'"{out_dir}/checkv" -d {checkv_db} -t {threads}'
            )
            lines.append(
                f'{bowtie2} -x "{out_dir}/viral_index" '
                f'-1 "{sample.r1}" -2 "{sample.r2}" | '
                f'{samtools} sort -@ {threads} -o "{out_dir}/mapped.bam"'
            )

    return "\n".join(lines) + ("\n" if lines else "")


def _mag_pipeline_script(
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    trim = _tool(envs, "trimmomatic")
    megahit = _tool(envs, "megahit")
    basalt = _tool(envs, "basalt")
    checkm = _tool(envs, "checkm")
    drep = _tool(envs, "drep")
    gtdbtk = _tool(envs, "gtdbtk")
    coverm = _tool(envs, "coverm")
    gtdbtk_db = _db(envs, "gtdbtk_db")

    lines: list[str] = []

    if script_name == "01_trimming.sh":
        for sample in samples:
            out_r1 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R1.fastq.gz"
            out_r2 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R2.fastq.gz"
            lines.append(
                f'{trim} PE -threads {threads} '
                f'"{sample.r1}" "{sample.r2}" '
                f'"{out_r1}" /dev/null "{out_r2}" /dev/null'
            )
    elif script_name == "02_assembly.sh":
        for sample in samples:
            clean_r1 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R1.fastq.gz"
            clean_r2 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R2.fastq.gz"
            out_dir = work_dir / "results" / "assembly" / sample.sample_id
            lines.append(
                f'{megahit} -1 "{clean_r1}" -2 "{clean_r2}" '
                f'-o "{out_dir}" -t {threads}'
            )
    elif script_name == "03_binning.sh":
        for sample in samples:
            contigs = work_dir / "results" / "assembly" / sample.sample_id / "final.contigs.fa"
            out_dir = work_dir / "results" / "binning" / sample.sample_id
            lines.append(
                f'{basalt} --contigs "{contigs}" --output "{out_dir}" -t {threads}'
            )
    elif script_name == "04_mag_qc.sh":
        bins_dir = work_dir / "results" / "binning"
        qc_dir = work_dir / "results" / "mag_qc"
        lines.append(f'{checkm} lineage_wf -t {threads} -x fa --tab_table -f "{qc_dir}" "{bins_dir}"')
        lines.append(
            f'{drep} -d "{bins_dir}" -o "{work_dir / "results" / "dereplication"}" '
            f'-pa 0.9 -sa 0.95'
        )
        lines.append(
            f'{gtdbtk} classify_wf --genome_dir "{work_dir / "results" / "dereplication"}" '
            f'--out_dir "{work_dir / "results" / "taxonomy"}" '
            f'--cpus {threads} --skip_ani_screen'
        )
        for sample in samples:
            lines.append(
                f'{coverm} genome --bam-files "{work_dir}/results/abundance/{sample.sample_id}.bam" '
                f'--genome-fasta-directory "{work_dir / "results" / "dereplication"}" '
                f'-o "{work_dir / "results" / "abundance" / sample.sample_id}_coverm.tsv"'
            )

    return "\n".join(lines) + ("\n" if lines else "")


def _read_based_risk_script(
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    trim = _tool(envs, "trimmomatic")
    kraken2 = _tool(envs, "kraken2")
    taxonkit = _tool(envs, "taxonkit")
    kraken2_db = _db(envs, "kraken2_db")
    pathogen_db = _db(envs, "pathogen_db")

    lines: list[str] = []

    if script_name == "01_trimming.sh":
        for sample in samples:
            out_r1 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R1.fastq.gz"
            out_r2 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R2.fastq.gz"
            lines.append(
                f'{trim} PE -threads {threads} '
                f'"{sample.r1}" "{sample.r2}" '
                f'"{out_r1}" /dev/null "{out_r2}" /dev/null'
            )
    elif script_name == "02_classification.sh":
        for sample in samples:
            clean_r1 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R1.fastq.gz"
            clean_r2 = work_dir / "results" / "clean_reads" / f"{sample.sample_id}_R2.fastq.gz"
            out_file = work_dir / "results" / "classification" / f"{sample.sample_id}.kraken2.out"
            lines.append(
                f'{kraken2} --db {kraken2_db} --paired '
                f'"{clean_r1}" "{clean_r2}" --threads {threads} '
                f'--output "{out_file}"'
            )
            lines.append(
                f'cat "{out_file}" | {taxonkit} lineage -i 2 | '
                f'{taxonkit} reformat -i 2 > '
                f'"{work_dir / "results" / "classification" / f"{sample.sample_id}.taxonomy.tsv"}"'
            )
    elif script_name == "03_pathogen_screening.sh":
        for sample in samples:
            tax_file = work_dir / "results" / "classification" / f"{sample.sample_id}.taxonomy.tsv"
            out_file = work_dir / "results" / "pathogen_screening" / f"{sample.sample_id}.hits.tsv"
            lines.append(
                f'# Compare {tax_file} against pathogen database at {pathogen_db}\n'
                f'echo "Pathogen screening placeholder for {sample.sample_id}" > "{out_file}"'
            )

    return "\n".join(lines) + ("\n" if lines else "")


def _micro_risk_script(
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    kraken2 = _tool(envs, "kraken2")
    pathogen_db = _db(envs, "pathogen_db")
    checkv_db = _db(envs, "checkv_db")

    lines: list[str] = []

    if script_name == "01_integrate_inputs.sh":
        lines.append(
            f'# Integrate virus_prediction, mag_pipeline, and read_based_risk outputs\n'
            f'mkdir -p "{work_dir / "results" / "integrated_inputs"}"'
        )
    elif script_name == "02_risk_assessment.sh":
        for sample in samples:
            out_file = work_dir / "results" / "risk_index" / f"{sample.sample_id}.risk.tsv"
            lines.append(
                f'# Combined risk scoring for {sample.sample_id}\n'
                f'# pathogen_db={pathogen_db}, checkv_db={checkv_db}\n'
                f'echo "Risk index placeholder for {sample.sample_id}" > "{out_file}"'
            )

    return "\n".join(lines) + ("\n" if lines else "")

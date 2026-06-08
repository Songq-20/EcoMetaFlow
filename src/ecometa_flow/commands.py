"""Generate realistic dry-run shell commands for each workflow module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ecometa_flow.envs import resolve_tool_command
from ecometa_flow.scanner import Sample


def _tool(envs: dict[str, Any], name: str) -> str:
    """Resolve a tool name to a shell command prefix or a readable placeholder."""
    tools = envs.get("tools", {})
    if name in tools:
        return resolve_tool_command(name, tools[name])
    return f"<{name}>"


def _tool_binary(envs: dict[str, Any], name: str, binary: str) -> str:
    """Resolve a companion binary that should run in the same environment."""
    tools = envs.get("tools", {})
    if name not in tools:
        return f"<{binary}>"

    entry = tools[name]
    mode = entry.get("mode", "command")
    if mode == "conda":
        env_path = entry.get("env", "")
        return f'conda run -p "{env_path}" {binary}'

    return binary


def _db(envs: dict[str, Any], name: str) -> str:
    """Resolve a database path or a readable placeholder."""
    databases = envs.get("databases", {})
    if name in databases:
        return str(databases[name])
    return f"<{name}_not_configured>"


def _clean_read_paths(work_dir: Path, sample: Sample) -> tuple[Path, Path]:
    """Return the standard clean-read output paths for one sample."""
    clean_dir = work_dir / "results" / "clean_reads"
    return (
        clean_dir / f"{sample.sample_id}_R1.fastq.gz",
        clean_dir / f"{sample.sample_id}_R2.fastq.gz",
    )


def _command_block(lines: list[str]) -> str:
    """Join shell command lines and keep the trailing newline for script output."""
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _escape_for_double_quotes(value: str) -> str:
    """Escape a string so it is safe inside one double-quoted shell argument."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _environment_script(module: str, envs: dict[str, Any]) -> str:
    """Build the shared environment-check script for one module."""
    module_tools: dict[str, list[str]] = {
        "virus_prediction": [
            "trimmomatic",
            "megahit",
            "virsorter2",
            "genomad",
            "vibrant",
            "checkv",
            "bowtie2",
            "samtools",
        ],
        "mag_pipeline": [
            "trimmomatic",
            "megahit",
            "basalt",
            "checkm",
            "drep",
            "gtdbtk",
            "coverm",
        ],
        "read_based_risk": [
            "trimmomatic",
            "kraken2",
            "taxonkit",
        ],
        "micro_risk": [
            "trimmomatic",
            "kraken2",
            "taxonkit",
            "bowtie2",
            "samtools",
        ],
    }
    module_databases: dict[str, list[str]] = {
        "virus_prediction": ["checkv_db"],
        "mag_pipeline": ["gtdbtk_db"],
        "read_based_risk": ["kraken2_db", "pathogen_db"],
        "micro_risk": ["kraken2_db", "pathogen_db", "checkv_db"],
    }

    lines = ['echo "Checking configured tools and databases for dry-run planning..."']
    for tool_name in module_tools.get(module, []):
        resolved = _escape_for_double_quotes(_tool(envs, tool_name))
        lines.append(f'echo "tool:{tool_name} => {resolved}"')
    for db_name in module_databases.get(module, []):
        resolved = _escape_for_double_quotes(_db(envs, db_name))
        lines.append(f'echo "database:{db_name} => {resolved}"')
    return _command_block(lines)


def generate_script_contents(
    module: str,
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    """Return the shell script body for a given module step."""
    header = (
        "#!/usr/bin/env bash\n"
        f"# EcoMetaFlow v0.2.0 dry-run workflow plan\n"
        f"# Module: {module}\n"
        f"# Script: {script_name}\n"
        "set -euo pipefail\n\n"
    )

    if script_name == "00_check_environment.sh":
        return header + _environment_script(module, envs)

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
    """Build dry-run commands for the virus prediction module."""
    trim = _tool(envs, "trimmomatic")
    megahit = _tool(envs, "megahit")
    virsorter = _tool(envs, "virsorter2")
    genomad = _tool(envs, "genomad")
    vibrant = _tool(envs, "vibrant")
    checkv = _tool(envs, "checkv")
    bowtie2 = _tool(envs, "bowtie2")
    bowtie2_build = _tool_binary(envs, "bowtie2", "bowtie2-build")
    samtools = _tool(envs, "samtools")
    checkv_db = _db(envs, "checkv_db")

    lines: list[str] = []

    if script_name == "01_trimming.sh":
        for sample in samples:
            out_r1, out_r2 = _clean_read_paths(work_dir, sample)
            lines.extend([
                f'echo "[virus_prediction] trimming {sample.sample_id}"',
                f'{trim} PE -threads {threads} '
                f'"{sample.r1}" "{sample.r2}" '
                f'"{out_r1}" /dev/null "{out_r2}" /dev/null '
                "ILLUMINACLIP:TruSeq3-PE.fa:2:30:10 "
                "LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
            ])
    elif script_name == "02_assembly.sh":
        for sample in samples:
            clean_r1, clean_r2 = _clean_read_paths(work_dir, sample)
            out_dir = work_dir / "results" / "assembly" / sample.sample_id
            lines.extend([
                f'echo "[virus_prediction] assembling {sample.sample_id}"',
                f'{megahit} -1 "{clean_r1}" -2 "{clean_r2}" '
                f'-o "{out_dir}" --out-prefix {sample.sample_id} -t {threads}',
            ])
    elif script_name == "03_virus_prediction.sh":
        for sample in samples:
            clean_r1, clean_r2 = _clean_read_paths(work_dir, sample)
            contigs = work_dir / "results" / "assembly" / sample.sample_id / "final.contigs.fa"
            sample_dir = work_dir / "results" / "virus_prediction" / sample.sample_id
            virsorter_dir = sample_dir / "virsorter2"
            genomad_dir = sample_dir / "genomad"
            vibrant_dir = sample_dir / "vibrant"
            checkv_dir = sample_dir / "checkv"
            votu_fasta = sample_dir / "votu" / "combined_viral_contigs.fa"
            taxonomy_tsv = sample_dir / "taxonomy" / "viral_taxonomy.tsv"
            mapping_dir = work_dir / "results" / "mapping" / sample.sample_id
            abundance_tsv = work_dir / "results" / "abundance" / f"{sample.sample_id}.viral_abundance.tsv"

            lines.extend([
                f'echo "[virus_prediction] predicting viral contigs for {sample.sample_id}"',
                f'mkdir -p "{virsorter_dir}" "{genomad_dir}" "{vibrant_dir}" '
                f'"{checkv_dir}" "{sample_dir / "votu"}" "{sample_dir / "taxonomy"}" "{mapping_dir}"',
                f'{virsorter} run -w "{virsorter_dir}" -i "{contigs}" '
                f'--min-length 1500 --include-groups dsDNAphage,NCLDV,RNA -j {threads} all',
                f'{genomad} end-to-end "{contigs}" "{genomad_dir}" --threads {threads}',
                f'{vibrant} -i "{contigs}" -folder "{vibrant_dir}" -t {threads}',
                f'{checkv} end_to_end "{virsorter_dir}/final-viral-combined.fa" '
                f'"{checkv_dir}" -d "{checkv_db}" -t {threads}',
                f'cat "{virsorter_dir}/final-viral-combined.fa" '
                f'"{genomad_dir}/final_viral_contigs.fna" '
                f'"{vibrant_dir}/VIBRANT_phages_{contigs.name}" > "{votu_fasta}"',
                f'awk \'BEGIN{{OFS="\\t"; print "contig_id","source"}} /^>/ {{gsub(/^>/, "", $1); print $1, "viral_catalog"}}\' '
                f'"{votu_fasta}" > "{taxonomy_tsv}"',
                f'{bowtie2_build} "{votu_fasta}" "{mapping_dir}/viral_index"',
                f'{bowtie2} -x "{mapping_dir}/viral_index" '
                f'-1 "{clean_r1}" -2 "{clean_r2}" --threads {threads} | '
                f'{samtools} sort -@ {threads} -o "{mapping_dir}/mapped.bam"',
                f'{samtools} index "{mapping_dir}/mapped.bam"',
                f'{samtools} idxstats "{mapping_dir}/mapped.bam" > "{abundance_tsv}"',
            ])

    return _command_block(lines)


def _mag_pipeline_script(
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    """Build dry-run commands for the MAG pipeline module."""
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
            out_r1, out_r2 = _clean_read_paths(work_dir, sample)
            lines.extend([
                f'echo "[mag_pipeline] trimming {sample.sample_id}"',
                f'{trim} PE -threads {threads} '
                f'"{sample.r1}" "{sample.r2}" '
                f'"{out_r1}" /dev/null "{out_r2}" /dev/null '
                "LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:50",
            ])
    elif script_name == "02_assembly.sh":
        for sample in samples:
            clean_r1, clean_r2 = _clean_read_paths(work_dir, sample)
            out_dir = work_dir / "results" / "assembly" / sample.sample_id
            lines.extend([
                f'echo "[mag_pipeline] assembling {sample.sample_id}"',
                f'{megahit} -1 "{clean_r1}" -2 "{clean_r2}" '
                f'-o "{out_dir}" --min-contig-len 1500 -t {threads}',
            ])
    elif script_name == "03_binning.sh":
        for sample in samples:
            clean_r1, clean_r2 = _clean_read_paths(work_dir, sample)
            contigs = work_dir / "results" / "assembly" / sample.sample_id / "final.contigs.fa"
            out_dir = work_dir / "results" / "binning" / sample.sample_id
            lines.extend([
                f'echo "[mag_pipeline] binning {sample.sample_id}"',
                f'mkdir -p "{out_dir}"',
                f'{basalt} auto -a "{contigs}" '
                f'-s "{clean_r1},{clean_r2}" -o "{out_dir}" -t {threads}',
            ])
    elif script_name == "04_mag_qc.sh":
        derep_dir = work_dir / "results" / "dereplication"
        taxonomy_dir = work_dir / "results" / "taxonomy"
        abundance_dir = work_dir / "results" / "abundance"
        lines.extend([
            'echo "[mag_pipeline] running bin quality control"',
            f'mkdir -p "{derep_dir}" "{taxonomy_dir}" "{abundance_dir}"',
        ])
        for sample in samples:
            bins_dir = work_dir / "results" / "binning" / sample.sample_id / "bins"
            sample_qc_dir = work_dir / "results" / "mag_qc" / sample.sample_id
            lines.append(
                f'{checkm} lineage_wf -t {threads} -x fa "{bins_dir}" "{sample_qc_dir}"'
            )
        lines.extend([
            f'{drep} dereplicate "{derep_dir}" '
            f'-g {work_dir}/results/binning/*/bins/*.fa -p {threads}',
            f'GTDBTK_DATA_PATH="{gtdbtk_db}" {gtdbtk} classify_wf '
            f'--genome_dir "{derep_dir}/dereplicated_genomes" '
            f'--out_dir "{taxonomy_dir}" --cpus {threads} --skip_ani_screen',
        ])
        for sample in samples:
            clean_r1, clean_r2 = _clean_read_paths(work_dir, sample)
            out_tsv = abundance_dir / f"{sample.sample_id}_coverm.tsv"
            lines.append(
                f'{coverm} genome -1 "{clean_r1}" -2 "{clean_r2}" '
                f'--genome-fasta-directory "{derep_dir}/dereplicated_genomes" '
                f'--methods relative_abundance covered_fraction '
                f'--threads {threads} -o "{out_tsv}"'
            )

    return _command_block(lines)


def _read_based_risk_script(
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    """Build dry-run commands for the read-based microbial risk module."""
    trim = _tool(envs, "trimmomatic")
    kraken2 = _tool(envs, "kraken2")
    taxonkit = _tool(envs, "taxonkit")
    kraken2_db = _db(envs, "kraken2_db")
    pathogen_db = _db(envs, "pathogen_db")

    lines: list[str] = []

    if script_name == "01_trimming.sh":
        for sample in samples:
            out_r1, out_r2 = _clean_read_paths(work_dir, sample)
            lines.extend([
                f'echo "[read_based_risk] trimming {sample.sample_id}"',
                f'{trim} PE -threads {threads} '
                f'"{sample.r1}" "{sample.r2}" '
                f'"{out_r1}" /dev/null "{out_r2}" /dev/null '
                "LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:50",
            ])
    elif script_name == "02_classification.sh":
        for sample in samples:
            clean_r1, clean_r2 = _clean_read_paths(work_dir, sample)
            class_dir = work_dir / "results" / "classification"
            report_file = class_dir / f"{sample.sample_id}.kraken2.report"
            out_file = class_dir / f"{sample.sample_id}.kraken2.out"
            taxonomy_file = class_dir / f"{sample.sample_id}.taxonomy.tsv"
            lines.extend([
                f'echo "[read_based_risk] classifying {sample.sample_id}"',
                f'{kraken2} --db "{kraken2_db}" --paired '
                f'"{clean_r1}" "{clean_r2}" --threads {threads} '
                f'--report "{report_file}" --output "{out_file}"',
                f'cut -f2,3 "{report_file}" | {taxonkit} lineage -i 2 | '
                f'{taxonkit} reformat -i 2 > "{taxonomy_file}"',
            ])
    elif script_name == "03_pathogen_screening.sh":
        for sample in samples:
            tax_file = work_dir / "results" / "classification" / f"{sample.sample_id}.taxonomy.tsv"
            out_file = work_dir / "results" / "pathogen_screening" / f"{sample.sample_id}.hits.tsv"
            summary_file = work_dir / "results" / "abundance" / f"{sample.sample_id}.pathogen_summary.tsv"
            lines.extend([
                f'echo "[read_based_risk] screening pathogens for {sample.sample_id}"',
                f'grep -F -f "{pathogen_db}" "{tax_file}" > "{out_file}" || true',
                f'awk \'BEGIN{{OFS="\\t"; print "sample_id","pathogen_hits"}} '
                f'END{{print "{sample.sample_id}", NR}}\' "{out_file}" > "{summary_file}"',
            ])

    return _command_block(lines)


def _micro_risk_script(
    script_name: str,
    samples: list[Sample],
    work_dir: Path,
    envs: dict[str, Any],
    threads: int,
) -> str:
    """Build dry-run commands for the integrated microbial risk module."""
    trim = _tool(envs, "trimmomatic")
    kraken2 = _tool(envs, "kraken2")
    taxonkit = _tool(envs, "taxonkit")
    bowtie2 = _tool(envs, "bowtie2")
    bowtie2_build = _tool_binary(envs, "bowtie2", "bowtie2-build")
    samtools = _tool(envs, "samtools")
    kraken2_db = _db(envs, "kraken2_db")
    pathogen_db = _db(envs, "pathogen_db")
    checkv_db = _db(envs, "checkv_db")

    lines: list[str] = []

    if script_name == "01_integrate_inputs.sh":
        integrated_dir = work_dir / "results" / "integrated_inputs"
        lines.extend([
            'echo "[micro_risk] linking upstream module outputs"',
            f'mkdir -p "{integrated_dir}"',
            'VIRUS_DIR="${ECOMETA_VIRUS_DIR:-<virus_prediction_workdir>}"',
            'MAG_DIR="${ECOMETA_MAG_DIR:-<mag_pipeline_workdir>}"',
            'READ_RISK_DIR="${ECOMETA_READ_RISK_DIR:-<read_based_risk_workdir>}"',
            f'ln -sfn "$VIRUS_DIR/results/virus_prediction" "{integrated_dir / "virus_prediction"}"',
            f'ln -sfn "$MAG_DIR/results/dereplication" "{integrated_dir / "dereplication"}"',
            f'ln -sfn "$READ_RISK_DIR/results/pathogen_screening" "{integrated_dir / "pathogen_screening"}"',
        ])
    elif script_name == "02_risk_assessment.sh":
        virus_catalog = work_dir / "results" / "integrated_inputs" / "virus_prediction"
        derep_dir = work_dir / "results" / "integrated_inputs" / "dereplication"
        for sample in samples:
            clean_r1 = work_dir / "tmp" / f"{sample.sample_id}_R1.clean.fastq.gz"
            clean_r2 = work_dir / "tmp" / f"{sample.sample_id}_R2.clean.fastq.gz"
            taxonomy_file = work_dir / "results" / "reports" / f"{sample.sample_id}.taxonomy.tsv"
            pathogen_hits = work_dir / "results" / "reports" / f"{sample.sample_id}.pathogen_hits.tsv"
            viral_bam = work_dir / "results" / "viral_risk" / f"{sample.sample_id}.bam"
            viral_stats = work_dir / "results" / "viral_risk" / f"{sample.sample_id}.idxstats.tsv"
            mag_catalog = work_dir / "tmp" / f"{sample.sample_id}.mag_catalog.fa"
            prok_bam = work_dir / "results" / "prokaryotic_risk" / f"{sample.sample_id}.bam"
            prok_stats = work_dir / "results" / "prokaryotic_risk" / f"{sample.sample_id}.idxstats.tsv"
            risk_index = work_dir / "results" / "risk_index" / f"{sample.sample_id}.risk.tsv"

            lines.extend([
                f'echo "[micro_risk] calculating integrated risk for {sample.sample_id}"',
                f'{trim} PE -threads {threads} '
                f'"{sample.r1}" "{sample.r2}" '
                f'"{clean_r1}" /dev/null "{clean_r2}" /dev/null '
                "LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:50",
                f'{kraken2} --db "{kraken2_db}" --paired '
                f'"{clean_r1}" "{clean_r2}" --threads {threads} '
                f'--report "{work_dir / "results" / "reports" / f"{sample.sample_id}.kraken2.report"}" '
                f'--output "{work_dir / "results" / "reports" / f"{sample.sample_id}.kraken2.out"}"',
                f'cut -f2,3 "{work_dir / "results" / "reports" / f"{sample.sample_id}.kraken2.report"}" | '
                f'{taxonkit} lineage -i 2 | {taxonkit} reformat -i 2 > "{taxonomy_file}"',
                f'grep -F -f "{pathogen_db}" "{taxonomy_file}" > "{pathogen_hits}" || true',
                f'cat {virus_catalog}/*/votu/combined_viral_contigs.fa > "{work_dir / "tmp" / "viral_catalog.fa"}"',
                f'{bowtie2_build} "{work_dir / "tmp" / "viral_catalog.fa"}" "{work_dir / "tmp" / "viral_catalog"}"',
                f'{bowtie2} -x "{work_dir / "tmp" / "viral_catalog"}" '
                f'-1 "{clean_r1}" -2 "{clean_r2}" --threads {threads} | '
                f'{samtools} sort -@ {threads} -o "{viral_bam}"',
                f'{samtools} index "{viral_bam}"',
                f'{samtools} idxstats "{viral_bam}" > "{viral_stats}"',
                f'cat {derep_dir}/dereplicated_genomes/*.fa > "{mag_catalog}"',
                f'{bowtie2_build} "{mag_catalog}" "{work_dir / "tmp" / f"{sample.sample_id}.mag_catalog"}"',
                f'{bowtie2} -x "{work_dir / "tmp" / f"{sample.sample_id}.mag_catalog"}" '
                f'-1 "{clean_r1}" -2 "{clean_r2}" --threads {threads} | '
                f'{samtools} sort -@ {threads} -o "{prok_bam}"',
                f'{samtools} index "{prok_bam}"',
                f'{samtools} idxstats "{prok_bam}" > "{prok_stats}"',
                f'awk -v sample="{sample.sample_id}" -v checkv_db="{checkv_db}" \''
                "BEGIN{OFS=\"\\t\"; viral=0; prok=0} "
                "FNR==NR {viral += $3; next} "
                "{prok += $3} "
                "END {print \"sample_id\",\"viral_reads\",\"prokaryotic_reads\",\"checkv_db\"; "
                "print sample, viral, prok, checkv_db}"
                f'\' "{viral_stats}" "{prok_stats}" > "{risk_index}"',
            ])

    return _command_block(lines)

"""Work directory layouts for each workflow module."""

from __future__ import annotations

from pathlib import Path

# Subdirectories created under the work root for every module.
COMMON_DIRS = [
    "config",
    "data",
    "logs",
    "scripts",
    "tmp",
]

# Module-specific result subdirectories under work/results/.
MODULE_RESULT_DIRS: dict[str, list[str]] = {
    "virus_prediction": [
        "clean_reads",
        "assembly",
        "virus_prediction",
        "mapping",
        "abundance",
    ],
    "mag_pipeline": [
        "clean_reads",
        "assembly",
        "binning",
        "mag_qc",
        "dereplication",
        "taxonomy",
        "abundance",
    ],
    "read_based_risk": [
        "clean_reads",
        "classification",
        "pathogen_screening",
        "abundance",
    ],
    "micro_risk": [
        "integrated_inputs",
        "viral_risk",
        "prokaryotic_risk",
        "risk_index",
        "reports",
    ],
}

# Shell script filenames generated per module.
MODULE_SCRIPTS: dict[str, list[str]] = {
    "virus_prediction": [
        "00_check_environment.sh",
        "01_trimming.sh",
        "02_assembly.sh",
        "03_virus_prediction.sh",
    ],
    "mag_pipeline": [
        "00_check_environment.sh",
        "01_trimming.sh",
        "02_assembly.sh",
        "03_binning.sh",
        "04_mag_qc.sh",
    ],
    "read_based_risk": [
        "00_check_environment.sh",
        "01_trimming.sh",
        "02_classification.sh",
        "03_pathogen_screening.sh",
    ],
    "micro_risk": [
        "00_check_environment.sh",
        "01_integrate_inputs.sh",
        "02_risk_assessment.sh",
    ],
}


def get_work_directories(module: str, work_dir: Path) -> list[Path]:
    """Return every directory that should be created for a module run."""
    dirs = [work_dir / name for name in COMMON_DIRS]
    dirs.append(work_dir / "results")

    for sub in MODULE_RESULT_DIRS.get(module, []):
        dirs.append(work_dir / "results" / sub)

    return dirs

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import configparser
import re
import shutil
from collections import namedtuple
from pathlib import Path
from typing import Iterable, Set

import pandas as pd

import dycov
from dycov.core.global_variables import CASE_SEPARATOR
from dycov.logging.logging import dycov_logging

ModelFiles = namedtuple("ModelFiles", ["model_path", "omega_path", "pcs_path", "benchmark"])
ProducerFiles = namedtuple("ProducerFiles", ["producer_dyd", "producer_par"])
_PKG_ROOT = Path(dycov.__file__).resolve().parent
_LATEX_ASSETS = [
    _PKG_ROOT / "templates/reports/step_response_characteristics.png",
    _PKG_ROOT / "templates/reports/TSO_logo.pdf",
    _PKG_ROOT / "templates/reports/fig_placeholder.pdf",
]


def should_copy(file: Path, extra_excludes: Iterable[re.Pattern] = ()) -> bool:
    """Checks if a file should be copied based on exclusion patterns.

    Parameters
    ----------
    file : Path
        File to evaluate
    extra_excludes : Iterable[re.Pattern], optional
        Additional regex patterns to exclude

    Returns
    -------
    bool
        True if the file should be copied, False otherwise
    """
    return file.is_file() and not any(p.match(str(file)) for p in extra_excludes)


def copy_file(source: Path, target: Path) -> None:
    """Copy from source to target.

    Parameters
    ----------
    source : Path
        Path to the file to copy
    target : Path
        Path where the copy of the file is created
    """
    dycov_logging.get_logger("Manage files").debug(f"Copying {source} to {target}")
    shutil.copy(source, target)


def rename_path(source: Path, target: Path) -> None:
    """Rename a file or directory from source to target.

    Parameters
    ----------
    source : Path
        Path to the file or directory to rename.
    target : Path
        New path for the file or directory.
    """
    if target.is_dir() and target.exists():
        shutil.rmtree(target)
    shutil.move(source, target)


def create_dir(path: Path, clean_first: bool = True, all_permissions: bool = False) -> None:
    """Create a directory at the specified path.

    Parameters
    ----------
    path : Path
        Directory path to create.
    clean_first : bool, optional
        If True, remove existing directory before creating (default is True).
    all_permissions : bool, optional
        If True, set permissions to 777 for the created directory (default is False).
    """
    if path.exists() and clean_first:
        shutil.rmtree(path)
    elif path.exists():
        return
    path.mkdir(parents=True)
    if all_permissions:
        path.chmod(0o777)


def remove_dir(path: Path) -> None:
    """Remove a directory and all its contents.

    Parameters
    ----------
    path : Path
        Directory path to remove.
    """
    if path.exists():
        shutil.rmtree(path)


def list_directories(source_path: Path) -> Set[str]:
    """List all non-hidden directories in the given path.

    Parameters
    ----------
    source_path : Path
        Path to search for directories.

    Returns
    -------
    Set[str]
        Set of directory names excluding hidden ones.
    """
    exclude_hidden = re.compile(r"^\.")
    return {
        entry.name
        for entry in source_path.iterdir()
        if entry.is_dir() and not exclude_hidden.match(entry.name)
    }


def check_output_dir(path: Path, force_overwrite: bool = False) -> bool:
    """Check if an output directory exists and handle overwrite confirmation.

    Parameters
    ----------
    path : Path
        Path to the output directory.
    force_overwrite : bool, optional
        If True, overwrite without asking (default is False).

    Returns
    -------
    bool
        True if the directory should NOT be overwritten, False otherwise.
    """
    if path.exists() and next(path.iterdir(), None):
        option = input("Do you want to overwrite the results directory? (y/[N]]) ")
        if option.lower() in ("n", "no", ""):
            return True
        shutil.rmtree(path)
    return False


def copy_from_path(source: Path, target: Path, extra_excludes: Iterable[re.Pattern] = ()) -> None:
    """Copy files from source to target, applying exclusion patterns.

    Parameters
    ----------
    source : Path
        Source file or directory.
    target : Path
        Destination directory.
    extra_excludes : Iterable[re.Pattern], optional
        Regex patterns for files to exclude.
    """
    if source.is_file():
        copy_file(source, target)
        return
    if not source.exists():
        return
    for file in source.iterdir():
        if should_copy(file, extra_excludes):
            copy_file(file, target / (file.stem + file.suffix.lower()))


def copy_directory(
    source: Path,
    target: Path,
    subpath: str = None,
    clean_init: bool = False,
    dirs_exist_ok: bool = False,
) -> None:
    """Copy a directory tree from source to target.

    Parameters
    ----------
    source : Path
        Source directory.
    target : Path
        Destination directory.
    subpath : str, optional
        Subdirectory to copy (default is None).
    clean_init : bool, optional
        If True, remove __init__.py and __pycache__ after copy (default is False).
    dirs_exist_ok : bool, optional
        If True, allow existing directories (default is False).
    """
    src = source / subpath if subpath else source
    dst = target / subpath if subpath else target
    shutil.copytree(src, dst, dirs_exist_ok=dirs_exist_ok)
    if clean_init:
        for file in dst.glob("**/__init__.py"):
            file.unlink()
        for cache_dir in dst.glob("**/__pycache__"):
            shutil.rmtree(cache_dir)


def clone_as_subdirectory(source_path: Path, name: str) -> Path:
    """Clone a directory as a subdirectory, excluding CSV files.

    Parameters
    ----------
    source_path : Path
        Source directory.
    name : str
        Name of the new subdirectory.

    Returns
    -------
    Path
        Path to the created subdirectory.
    """
    created_path = source_path / name
    create_dir(created_path)
    exclude_csv = [re.compile(r".*\.[cC][sS][vV]$")]
    copy_from_path(source_path, created_path, extra_excludes=exclude_csv)
    return created_path


def copy_base_case_files(
    model_files: ModelFiles, producer_files: ProducerFiles, target_path: Path
) -> None:
    """Copy base case files for models and producers to target directory.

    Parameters
    ----------
    model_files : ModelFiles
        Named tuple containing model-related paths.
    producer_files : ProducerFiles
        Named tuple containing producer-related files.
    target_path : Path
        Destination directory.
    """
    # Context-specific exclusions
    exclude_patterns = [
        re.compile(r".*__init__.py"),
        re.compile(r".*__pycache__.*"),
        re.compile(r".*\.[iI][nN][iI]$"),
        re.compile(r".*\.[cC][rR][vV]$"),
    ]
    copy_from_path(model_files.model_path, target_path)
    copy_from_path(model_files.omega_path, target_path)
    copy_from_path(model_files.pcs_path, target_path, extra_excludes=exclude_patterns)
    benchmark_path = model_files.pcs_path / model_files.benchmark
    if benchmark_path.exists():
        copy_from_path(benchmark_path, target_path, extra_excludes=exclude_patterns)
    copy_from_path(
        model_files.model_path.parent.parent, target_path, extra_excludes=exclude_patterns
    )
    for file in [producer_files.producer_dyd, producer_files.producer_par]:
        copy_file(file, target_path / (file.stem + file.suffix.lower()))


def copy_base_curves_files(source_path: Path, target_path: Path, prefix_name: str) -> bool:
    """Copy curve files based on prefix name from source to target.

    Parameters
    ----------
    source_path : Path
        Directory containing curve files.
    target_path : Path
        Destination directory.
    prefix_name : str
        Prefix used to identify curve files.

    Returns
    -------
    bool
        True if curves were successfully copied, False otherwise.
    """
    curves_dir = source_path
    if not curves_dir.exists():
        return False
    try:
        if (curves_dir / "CurvesFiles.ini").exists():
            copy_file(curves_dir / "CurvesFiles.ini", target_path)
            curves_cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
            curves_cfg.read(curves_dir / "CurvesFiles.ini")
            curves_filename = curves_cfg.get("Curves-Files", prefix_name, fallback=None)
            file_copied = None
            if curves_filename:
                curves_file = curves_dir / curves_filename
                if curves_file.exists():
                    copy_file(
                        curves_file, target_path / (prefix_name + curves_file.suffix.lower())
                    )
                    file_copied = curves_file.stem
            if file_copied is None:
                pattern = re.compile(rf".*{prefix_name}\.[cC][sS][vV]")
                for file in curves_dir.iterdir():
                    if pattern.match(file.name):
                        copy_file(file, target_path / f"{prefix_name}.{file.suffix.lower()}")
                        file_copied = file.stem
            success = False
            if file_copied:
                dict_pattern = re.compile(rf".*{file_copied}\.[dD][iI][cC][tT]")
                for file in curves_dir.iterdir():
                    if dict_pattern.match(file.name):
                        copy_file(file, target_path / (file_copied + file.suffix.lower()))
                        success = True
            return success
    except OSError:
        dycov_logging.get_logger("Manage files").warning(
            "The supplied curves set has not been updated"
        )
    return False


def copy_latex_files(source: Path, target: Path, prefix_name: str) -> None:
    """Copy LaTeX files and additional resources to target directory.

    Parameters
    ----------
    source : Path
        Source directory containing LaTeX files.
    target : Path
        Destination directory.
    prefix_name : str
        Prefix for LaTeX file names.
    """
    tex_pattern = re.compile(r".*\.tex")
    tex_pattern2 = re.compile(r"common*")
    for file in source.iterdir():
        if tex_pattern.match(file.name) and not tex_pattern2.match(file.name):
            copy_file(file, target / f"{prefix_name}.{file.name}")
        else:
            copy_file(file, target)

    for asset in _LATEX_ASSETS:
        copy_file(asset, target)


def create_config_file(config_file: Path, target_file: Path) -> None:
    """Create a configuration file by commenting non-essential lines.

    Parameters
    ----------
    config_file : Path
        Source configuration file.
    target_file : Path
        Destination configuration file.
    """
    with open(config_file, "r") as input_file, open(target_file, "w") as output_file:
        for line in input_file:
            if (
                line.startswith("[")
                or len(line) == 1
                or line.startswith(("version = ", "type = "))
            ):
                output_file.write(line)
            else:
                output_file.write("# " + line)


def move_report(source: Path, target: Path, report_name: str) -> bool:
    """Move a report file (PDF or log) from source to target.

    Parameters
    ----------
    source : Path
        Directory containing the report.
    target : Path
        Destination directory.
    report_name : str
        Name of the report (used to derive file name).

    Returns
    -------
    bool
        True if PDF report was moved, False otherwise.
    """
    pdf_file = source / (report_name.split(CASE_SEPARATOR)[0] + ".pdf")
    dycov_logging.get_logger("Manage files").debug(f"Moving report {pdf_file} to {target}")
    if not pdf_file.exists():
        copy_file(source / (report_name.split(CASE_SEPARATOR)[0] + ".log"), target)
        return False
    copy_file(pdf_file, target)
    return True


def read_curves(file: Path) -> pd.DataFrame:
    """Read a curves CSV file into a pandas DataFrame.

    Parameters
    ----------
    file : Path
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        DataFrame containing curve data.
    """
    return pd.read_csv(file, sep=";")

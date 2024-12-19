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
import logging
import re
import shutil
from collections import namedtuple
from pathlib import Path

import pandas as pd

from dgcv.core.global_variables import CASE_SEPARATOR
from dgcv.logging.logging import dgcv_logging

ModelFiles = namedtuple("ModelFiles", ["model_path", "omega_path", "pcs_path", "benchmark"])
ProducerFiles = namedtuple("ProducerFiles", ["producer_dyd", "producer_par"])


def _copy_files(
    path: Path,
    target_path: Path,
):
    pattern = re.compile(r".*")
    exclude_pattern1 = re.compile(r".*__init__.py")
    exclude_pattern2 = re.compile(r".*__pycache__*")
    for file in path.iterdir():
        matching = pattern.match(str(file))
        matching1 = exclude_pattern1.match(str(file))
        matching2 = exclude_pattern2.match(str(file))
        if matching and not matching1 and not matching2:
            shutil.copy(file, target_path / (file.stem + file.suffix.lower()))


def create_config_file(config_file: Path, target_file: Path) -> None:
    """Create a commented config file in target from the input config file.

    Parameters
    ----------
    config_file: Path
        Input config file
    target: Path
        Target path
    """
    with open(config_file, "r") as input_file:
        with open(target_file, "w") as output_file:
            for line in input_file:
                if line.startswith("[") or len(line) == 1:
                    output_file.write(line)
                elif line.startswith("version = ") or line.startswith("type = "):
                    output_file.write(line)
                else:
                    output_file.write("#  " + line)


def check_output_dir(path: Path) -> int:
    """Check if a path exists, if so it offers the possibility to delete it.

    Parameters
    ----------
    path: Path
        Path to check if exists

    Returns
    -------
    bool
        True if the path exists and the user does not want to delete it,
        False otherwise
    """
    if path.exists() and next(path.iterdir(), None):
        option = input("Do you want to overwrite the results directory? (y/[N]]) ")
        if option in ("N", "n", "no", "No", "NO", ""):
            return True
        else:
            remove_dir(path)

    return False


def create_dir(path: Path, clean_first: bool = True, all: bool = False) -> None:
    """Create a new directory, deleting the old one if it already existed.

    Parameters
    ----------
    path: Path
        Path to the new directory
    clean_first: bool
        Remove the path if exists
    all: bool
        Create the path will all active permissions
    """
    if path.exists() and clean_first:
        remove_dir(path)
    elif path.exists():
        return

    path.mkdir(parents=True)
    if all:
        path.chmod(0o777)


def remove_dir(path: Path) -> None:
    """Delete a directory and its contents.

    Parameters
    ----------
    path: Path
        Path to the directory
    """
    if path.exists():
        shutil.rmtree(path)


def clone_as_subdirectory(source_path: Path, name: str) -> Path:
    """Clone source in a new subdirectory.

    Parameters
    ----------
    source_path: Path
        Source path
    name: str
        Name to the new directory

    Returns
    -------
    Path
        Path to the new subdirectory
    """
    created_path = source_path / name
    create_dir(created_path)

    shutil.copytree(
        source_path,
        created_path,
        dirs_exist_ok=True,
    )

    for path in created_path.iterdir():
        if path.is_dir():
            remove_dir(created_path / path)

    (created_path / "curves_final.csv").unlink(missing_ok=True)
    (created_path / "curves_final2.csv").unlink(missing_ok=True)
    return created_path


def list_directories(source_path: Path) -> set:
    """Gets a listing of the contents of source.

    Parameters
    ----------
    source_path: Path
        Parent path

    Returns
    -------
    set
        directories contained in the composed path
    """
    pattern = re.compile(r".*")
    exclude_pattern1 = re.compile(r".*__init__.py")
    exclude_pattern2 = re.compile(r".*__pycache__*")
    exclude_hidden = re.compile(r"\.")

    pcs_list = set()
    for file in source_path.iterdir():
        matching = pattern.match(str(file))
        matching1 = exclude_pattern1.match(str(file))
        matching2 = exclude_pattern2.match(str(file))
        matching_hidden = exclude_hidden.match(file.resolve().name)
        if matching and not matching1 and not matching2 and not matching_hidden:
            pcs_list.add(file.resolve().name)

    return pcs_list


def copy_path(source_path: Path, target_path: Path) -> None:
    """Copy the content of source in target.

    Parameters
    ----------
    source_path: Path
        Parent path
    target_path: Path
        Target path
    """
    file_path = Path(__file__).resolve().parent.parent
    pcs_path = file_path / source_path
    shutil.copytree(pcs_path, target_path, dirs_exist_ok=True)

    for file in target_path.glob("**/__init__.py"):
        file.unlink()

    for cache_dir in target_path.glob("**/__pycache__"):
        shutil.rmtree(cache_dir)


def copy_base_case_files(
    model_files: ModelFiles,
    producer_files: ProducerFiles,
    target_path: Path,
) -> None:
    """Copies the model and producer files in the target directory.

    Parameters
    ----------
    model_files: ModelFiles
        Model template files
    producer_files: ProducerFiles
        Producer input files
    target_path: Path
        Target path
    """

    _copy_files(model_files.model_path, target_path)
    _copy_files(model_files.omega_path, target_path)

    pattern = re.compile(r".*")
    exclude_pattern1 = re.compile(r".*__init__.py")
    exclude_pattern2 = re.compile(r".*__pycache__*")
    exclude_pattern3 = re.compile(r".*.[iI][nN][iI]$")
    exclude_pattern4 = re.compile(r".*.[cC][rR][vV]$")
    for file in model_files.pcs_path.iterdir():
        matching = pattern.match(str(file))
        matching1 = exclude_pattern1.match(str(file))
        matching2 = exclude_pattern2.match(str(file))
        matching3 = exclude_pattern3.match(str(file))
        matching4 = exclude_pattern4.match(str(file))
        if (
            matching
            and not matching1
            and not matching2
            and not matching3
            and not matching4
            and not file.is_dir()
        ):
            shutil.copy(file, target_path / (file.stem + file.suffix.lower()))

    benchmark_path = model_files.pcs_path / model_files.benchmark
    if benchmark_path.exists():
        for file in benchmark_path.iterdir():
            matching = pattern.match(str(file))
            matching1 = exclude_pattern1.match(str(file))
            matching2 = exclude_pattern2.match(str(file))
            matching3 = exclude_pattern3.match(str(file))
            if matching and not matching1 and not matching2 and not matching3 and not matching4:
                shutil.copy(file, target_path / (file.stem + file.suffix.lower()))

    # Copy the jobs and cvr TSOModel files and solvers.par
    for file in (model_files.model_path / "../..").iterdir():
        matching = pattern.match(str(file))
        matching1 = exclude_pattern1.match(str(file))
        matching2 = exclude_pattern2.match(str(file))
        if matching and not matching1 and not matching2 and file.is_file():
            shutil.copy(file, target_path / (file.stem + file.suffix.lower()))

    # Copy the procuder files
    producer_dyd = producer_files.producer_dyd
    producer_par = producer_files.producer_par
    shutil.copy(producer_dyd, target_path / (producer_dyd.stem + producer_dyd.suffix.lower()))
    shutil.copy(producer_par, target_path / (producer_par.stem + producer_par.suffix.lower()))


def copy_base_curves_files(
    source_path: Path,
    target_path: Path,
    prefix_name: str,
) -> bool:
    """Copies the files which name starts with prefix_name, from source dir to target dir.

    Parameters
    ----------
    source_path: Path
        Source path
    target_path: Path
        Target path
    prefix_name: str
        Prefix filename

    Returns
    -------
    bool
        True if it ends successfully, False otherwise
    """
    curves_dir = source_path
    if not curves_dir.exists():
        return False

    try:
        if (curves_dir / "CurvesFiles.ini").exists():
            shutil.copy(curves_dir / "CurvesFiles.ini", target_path)

            curves_cfg = configparser.ConfigParser()
            curves_cfg.read(curves_dir / "CurvesFiles.ini")

            if not curves_cfg.has_option("Curves-Files", prefix_name):
                return False

            curves_filename = curves_cfg.get("Curves-Files", prefix_name)
            curves_file = curves_dir / curves_filename
            if not curves_file.exists():
                return False

            shutil.copy(curves_file, target_path / (prefix_name + curves_file.suffix.lower()))
        else:
            for file in curves_dir.glob(prefix_name + ".*"):
                shutil.copy(file, target_path / (prefix_name + file.suffix.lower()))

    except OSError:
        dgcv_logging.get_logger("Manage files").warning(
            "The supplied curves set has not been updated"
        )

    # copy the DICT file
    success = False
    for file in curves_dir.iterdir():
        if file.stem.startswith(prefix_name):
            shutil.copy(file, target_path / (file.stem + file.suffix.lower()))
            success = True

    return success


def rename_dir(source_path: Path, target_path: Path) -> None:
    """Rename a directoty.

    Parameters
    ----------
    source_path: Path
        Source path
    target_path: Path
        Target path
    """
    remove_dir(target_path)
    shutil.move(source_path, target_path)


def rename_file(source_file: Path, target_file: Path) -> None:
    """Rename a file.

    Parameters
    ----------
    source_file: Path
        Source file
    target_file: Path
        Target file
    """
    shutil.move(source_file, target_file)


def copy_output_files(pcs_name: str, source_path: Path, target_path: Path) -> None:
    """Copy the output files from source to target.

    Parameters
    ----------
    pcs_name: str
        Pcs name
    source_path: Path
        Source path
    target_path: Path
        Target path
    """
    source_pcs = source_path / pcs_name
    target_pcs = target_path / pcs_name
    shutil.copytree(source_pcs, target_pcs, dirs_exist_ok=True)


def copy_latex_files(source: Path, target: Path) -> None:
    """Copy LaTex templates files from source to target.

    Parameters
    ----------
    source_path: Path
        Source path
    target_path: Path
        Target path
    """
    pattern = re.compile(r".*")
    exclude_pattern1 = re.compile(r".*__init__.py")
    exclude_pattern2 = re.compile(r".*__pycache__*")
    exclude_hidden = re.compile(r"\.")
    for file in source.iterdir():
        matching = pattern.match(str(file))
        matching1 = exclude_pattern1.match(str(file))
        matching2 = exclude_pattern2.match(str(file))
        matching_hidden = exclude_hidden.match(file.resolve().name)
        if matching and not matching1 and not matching2 and not matching_hidden:
            shutil.copy(source / file, target)

    shutil.copy(source / "../../../step_response_characteristics.png", target)
    shutil.copy(source / "../../../TSO_logo.pdf", target)
    shutil.copy(source / "../../../fig_placeholder.pdf", target)


def move_report(
    source: Path,
    target: Path,
    report_name: str,
) -> bool:
    """Move the compiled LaTex file or log file from source to target.

    Parameters
    ----------
    source: Path
        Source path
    target: Path
        Target path
    report_name: str
        LaTex report filename

    Returns
    -------
    bool
        True if the LaTex successfully compiled the report, False otherwise
    """
    if not (source / (report_name.split(CASE_SEPARATOR)[0] + ".pdf")).exists():
        shutil.copy(
            source / (report_name.split(CASE_SEPARATOR)[0] + ".log"),
            target,
        )
        return False

    shutil.copy(
        source / (report_name.split(CASE_SEPARATOR)[0] + ".pdf"),
        target,
    )
    if dgcv_logging.getEffectiveLevel() != logging.DEBUG:
        shutil.rmtree(source)

    return True


def read_curves(file: Path) -> pd.DataFrame:
    """Import a curves file into a DataFrame.

    Parameters
    ----------
    file: Path
        Curve file

    Returns
    -------
    DataFrame
        A DataFrame with the imported curves
    """
    # Get curves file
    df_curves = pd.read_csv(file, sep=";")

    return df_curves

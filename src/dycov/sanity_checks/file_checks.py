#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""
This module provides functions for validating the presence, structure, and consistency
of various files related to Dynawo models and curves.
"""
import errno
import os
import re
from pathlib import Path

from lxml import etree

from dycov.files.producer_curves import create_producer_curves
from dycov.logging.logging import dycov_logging


def check_dynawo_model_files(model_path: Path, filename: str = "") -> None:
    """
    Checks for the presence of essential Dynawo model files (.dyd, .par, .ini)
    within the specified model path.

    Parameters
    ----------
    model_path : Path
        The path to the directory containing the Dynawo model files.
    filename : str, optional
        The base name of the model files (e.g., "model_name"). If empty,
        it checks for any .dyd, .par, .ini files. By default, "".

    Raises
    ------
    FileNotFoundError
        If any of the required .dyd, .par, or .ini files are missing,
        or if their base names do not match.
    """
    # Define regular expressions for .dyd, .par, and .ini files
    dyd_pattern = re.compile(rf".*{filename}.[dD][yY][dD]")
    par_pattern = re.compile(rf".*{filename}.[pP][aA][rR]")
    ini_pattern = re.compile(rf".*{filename}.[iI][nN][iI]")

    has_dyd = None
    has_par = None
    has_ini = None
    # Iterate through files in the model path to find required Dynawo input files
    for file in model_path.resolve().iterdir():
        if dyd_pattern.match(str(file)):
            has_dyd = file.stem
        if par_pattern.match(str(file)):
            has_par = file.stem
        if ini_pattern.match(str(file)):
            has_ini = file.stem

    # Check if the .dyd file is present; raise FileNotFoundError if not
    if not has_dyd:
        dycov_logging.get_logger("Sanity Checks").error(
            f"The dynawo model must contain a {filename}.dyd file with the model definition."
        )
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), f"Model {filename}.dyd file not found."
        )
    # Check if the .par file is present; raise FileNotFoundError if not
    if not has_par:
        dycov_logging.get_logger("Sanity Checks").error(
            f"The dynawo model must contain a {filename}.par file with the model parameters."
        )
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), f"Model {filename}.par file not found."
        )
    # Check if the .ini file is present; raise FileNotFoundError if not
    if not has_ini:
        dycov_logging.get_logger("Sanity Checks").error(
            f"The dynawo model must contain a {filename}.ini file with the model configuration."
        )
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), f"Model {filename}.ini file not found."
        )
    # Verify that all three files (.dyd, .par, .ini) share the same base name
    if has_dyd != has_par or has_dyd != has_ini:
        dycov_logging.get_logger("Sanity Checks").error(
            "The dynawo model must contain a .dyd, .par and .ini file with the same name."
        )
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            "Model files do not have the same name.",
        )


def check_well_formed_xml(xml_file: Path) -> None:
    """
    Checks if the supplied file is a well-formed XML file.

    Parameters
    ----------
    xml_file : Path
        Path to the XML file.

    Raises
    ------
    lxml.etree.XMLSyntaxError
        If the XML file is not well-formed.
    """
    etree.parse(open(xml_file))


def check_curves_files(model_path: Path, curves_path: Path, template: str) -> None:
    """
    Checks if the `CurvesFiles.ini` configuration file is present in the specified
    curves path. If not found and a model path is provided, it attempts to create it.

    Parameters
    ----------
    model_path : Path
        Path to the Dynawo model. Used to create curves if missing.
    curves_path : Path
        Path to the directory where curves files are expected.
    template : str
        Template name for the curves files (e.g., "model", "performance_scenario").

    Raises
    ------
    FileNotFoundError
        If `CurvesFiles.ini` is not found and cannot be created.
    """
    # If no curves path is provided, there's nothing to check
    if not curves_path:
        return

    # Check if 'CurvesFiles.ini' exists in the curves_path
    if not (curves_path / "CurvesFiles.ini").exists():
        message = ""
        # If a model path is provided, try to create the producer curves file
        if model_path:
            template_name = "model"
            if template.startswith("performance"):
                template_name = template.replace("/", "_")
            create_producer_curves(model_path, curves_path, template_name)
            message = " Edit the generated file to complete it."

        # Log an error and raise FileNotFoundError if 'CurvesFiles.ini' is still not found
        dycov_logging.get_logger("Sanity Checks").error(f"CurvesFiles.ini not found.{message}")
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "CurvesFiles.ini")


def check_performance_model(model_path: Path) -> None:
    """
    Checks if the Dynawo model files (.dyd, .par, .ini) are present in the
    specified performance model path.

    Parameters
    ----------
    model_path : Path
        Path to the Dynawo performance model.
    """
    # Delegate to the private helper function to check Dynawo input files
    check_dynawo_model_files(model_path)


def check_performance_curves(curves_path: Path) -> None:
    """
    Checks if configuration files (.ini) and their corresponding curve directories
    are present in the performance curves path.

    Parameters
    ----------
    curves_path : Path
        Path to the performance curves files.

    Raises
    ------
    FileNotFoundError
        If any configuration file or its corresponding curve directory is missing.
    """
    # Check if any .ini configuration file exists in the curves path
    if not any(curves_path.glob("*.[iI][nN][iI]")):
        dycov_logging.get_logger("Sanity Checks").error(
            "Configuration file is not present in the curves path."
        )
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            "Configuration file is not present in the curves path.",
        )

    # For each .ini file found, check if its corresponding directory of curves exists
    for ini_file in curves_path.glob("*.[iI][nN][iI]"):
        if not (curves_path / ini_file.stem).exists():
            dycov_logging.get_logger("Sanity Checks").error(
                f"Curves files for {ini_file.stem} are not present in the curves path."
            )
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                f"Curves files for {ini_file.stem} are not present in the curves path.",
            )


def check_zone_curves_and_references(
    zone_name: str, curves_path: Path, reference_path: Path
) -> None:
    """
    Helper function to check curves and references for a given zone (e.g., "Zone1" or "Zone3").

    Parameters
    ----------
    zone_name : str
        The name of the zone (e.g., "Zone1", "Zone3").
    curves_path : Path
        Base path to the curves files.
    reference_path : Path
        Base path to the reference curves.

    Raises
    ------
    FileNotFoundError
        If the zone directory or its configuration files are missing in the curves path.
    """
    # Construct the full path for the specific zone within curves_path
    zone_path = curves_path / zone_name
    # Check if the zone directory exists
    if not zone_path.is_dir():
        dycov_logging.get_logger("Sanity Checks").error(
            f"{zone_name} configuration files are not present in the curves path."
        )
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), f"{zone_name} configuration files not found."
        )

    # Check if any .ini file exists within the zone directory
    has_ini_file = any(zone_path.glob("*.[iI][nN][iI]"))
    if not has_ini_file:
        dycov_logging.get_logger("Sanity Checks").error(
            f"{zone_name} configuration files are not present in the curves path."
        )
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), f"{zone_name} configuration files not found."
        )

    # For each .ini file in the zone, check if its corresponding curves directory and reference
    # curves exist
    for ini_file in zone_path.glob("*.[iI][nN][iI]"):
        # Check if the curves directory for the .ini file exists
        if not (curves_path / ini_file.stem).exists():
            dycov_logging.get_logger("Sanity Checks").error(
                f"Curves files for {ini_file.stem} are not present in the curves path."
            )
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                f"Curves files for {ini_file.stem} are not present in the curves path.",
            )
        # Warn if reference curves for the .ini file's stem are not found in the reference path
        if not (reference_path / ini_file.stem).exists():
            dycov_logging.get_logger("Sanity Checks").warning(
                f"Reference curves for {ini_file.stem} are not present in the reference path."
            )


def check_validation_model(
    model_path: Path, reference_path: Path, z3_generators: int, z3_names: list, z1_names: list
) -> None:
    """
    Checks if the Dynawo model files for Zone1 and Zone3 are present,
    and if the number of Zone3 generators matches the number of Zone1 files.
    Also warns about missing reference curve files for Zone1 generators.

    Parameters
    ----------
    model_path : Path
        Path to the base directory of the Dynawo model (containing Zone1 and Zone3 subdirectories).
    reference_path : Path
        Path to the reference curves directory.
    z3_generators : int
        Number of Zone3 generators.
    z3_names : list
        List of Zone3 generator names.
    z1_names : list
        List of Zone1 generator names.

    Raises
    ------
    ValueError
        If the number of Zone3 generators does not match the number of Zone1 files.
    """
    # Check Dynawo inputs for the Zone3 model
    check_dynawo_model_files(model_path / "Zone3")
    # Verify that the number of Zone3 generators matches the number of Zone1 files
    if z3_generators != len(z1_names):
        dycov_logging.get_logger("Sanity Checks").error(
            "The number of Zone3 generators must match the number of Zone1 files."
        )
        raise ValueError("Zone3 generators and Zone1 files count mismatch.")
    # Check Dynawo inputs for each Zone1 model
    for z1_name in z1_names:
        check_dynawo_model_files(model_path / "Zone1", z1_name)

    # Iterate through directories in the reference path
    for file in reference_path.resolve().iterdir():
        if not file.is_dir():
            continue

        # Warn if a Zone1 generator's reference curve files are missing
        if file.name not in z1_names + z3_names:
            dycov_logging.get_logger("Sanity Checks").warning(
                f"Zone1 generator {file.stem} has not Reference curve files."
            )


def check_validation_curves(curves_path: Path, reference_path: Path) -> None:
    """
    Checks if the curves files are present for both Zone1 and Zone3 within the specified
    curves path, and if corresponding reference files exist.

    Parameters
    ----------
    curves_path : Path
        Path to the curves files directory (containing Zone1 and Zone3 subdirectories).
    reference_path : Path
        Path to the reference curves directory.
    """
    # Check curves and references for Zone1
    check_zone_curves_and_references("Zone1", curves_path, reference_path)
    # Check curves and references for Zone3
    check_zone_curves_and_references("Zone3", curves_path, reference_path)

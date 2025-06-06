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
This module provides functions for checking the availability of external system
executables required by the Dynawo validation tools.
"""
import os
import shutil
from pathlib import Path

from dycov.logging.logging import dycov_logging


def check_launchers(launcher_dwo: Path) -> None:
    """
    Check if the required launchers are available in the system.

    Parameters
    ----------
    launcher_dwo: Path
        Path to the Dynawo launcher.
    """
    error_txt = ""
    # Check if Dynawo launcher is found in system's PATH
    if not shutil.which(str(launcher_dwo)):  # shutil.which expects a string
        error_txt += "Dynawo not found.\n"
    # Check if PdfLatex is found in system's PATH
    if not shutil.which("pdflatex"):
        error_txt += "PdfLatex not found.\n"
    # Check if CMake is found in system's PATH
    if not shutil.which("cmake"):
        error_txt += "CMake not found.\n"
    # TODO: for Windows, add an analogous check for the presence of the VS2019 compiler.
    # Check if G++ is found in system's PATH (for POSIX systems)
    if os.name == "posix" and not shutil.which("g++"):
        error_txt += "G++ not found.\n"

    # If any required launcher is missing, raise an OSError
    if len(error_txt) > 0:
        raise OSError(error_txt)

    # Warn if 'open' command is not found on POSIX systems (less critical)
    if os.name == "posix" and not shutil.which("open"):
        dycov_logging.get_logger("Sanity Checks").warning("Open not found")

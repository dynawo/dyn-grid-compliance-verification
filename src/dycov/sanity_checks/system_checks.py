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

from dycov.logging import dycov_logging


def check_launchers(launcher_dwo: Path) -> None:
    """
    Check if the Dynawo launcher is available in the system.

    Parameters
    ----------
    launcher_dwo: Path
        Path to the Dynawo launcher.

    Raises
    ------
    OSError
        If the launcher is not found in the system PATH.

    """
    if not shutil.which(str(launcher_dwo)):  # shutil.which expects a string
        raise OSError("Dynawo not found.")


def check_report_tools() -> None:
    """
    Check if the executables the report needs are available in the system.

    Raises
    ------
    OSError
        If pdflatex, which compiles the report, is not found in the system PATH.

    """
    if not shutil.which("pdflatex"):
        raise OSError("PdfLatex not found.")

    # Warn if 'open' command is not found on POSIX systems (less critical)
    if os.name == "posix" and not shutil.which("open"):
        dycov_logging.get_logger("Sanity Checks").warning("Open not found")

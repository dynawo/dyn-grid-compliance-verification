#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import argparse
import os
import shutil
import sys

from dycov.logging.logging import dycov_logging
from dycov.sanity_checks import system_checks

_LOGGER = dycov_logging.get_logger("CliUtils")


def get_dynawo_launcher_name(parser: argparse.ArgumentParser, args: argparse.Namespace) -> str:
    """Determines the name or path of the Dynawo launcher.

    This function first attempts to retrieve the Dynawo launcher path from the provided
    command-line arguments. If not found, it defaults to a system-specific launcher name
    ("dynawo.cmd" for Windows, "dynawo.sh" for others). If the default launcher is not
    found in the system's PATH and the command is not 'anonymize' (which doesn't require
    the launcher), an error is raised, and the program exits.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The argument parser, used for raising errors and printing help messages.
    args: argparse.Namespace
        The parsed command-line arguments, containing the 'launcher' and 'command'
        attributes.

    Returns
    -------
    str
        The resolved name or path of the Dynawo launcher.
    """
    _LOGGER.debug("Getting Dynawo launcher name.")
    # Attempt to get the launcher from the arguments.
    dynawo_launcher_name = getattr(args, "launcher", None)

    if not dynawo_launcher_name:
        # Default to system-specific launcher name if not provided.
        dynawo_launcher_name = "dynawo.cmd" if os.name == "nt" else "dynawo.sh"
        _LOGGER.debug(f"No launcher specified, defaulting to: {dynawo_launcher_name}")

        # If the default launcher is not found in the system PATH
        # and the command is not 'anonymize' (which doesn't need it), show an error.
        if shutil.which(dynawo_launcher_name) is None and args.command != "anonymize":
            _LOGGER.critical(
                f"The default Dynawo launcher '{dynawo_launcher_name}' has not "
                "been found in PATH. Please provide a correct path using the -l argument."
            )
            parser.error(
                "The default Dynawo launcher has not been found, please "
                "provide a correct path using the -l argument."
            )
            # sys.exit(1) is handled by the calling function's error handling.
            # No explicit exit here to allow for centralized error management.

    _LOGGER.info(f"Dynawo launcher resolved to: {dynawo_launcher_name}")
    return dynawo_launcher_name


def check_dynawo_launcher_availability(dynawo_launcher_name: str) -> None:
    """Checks the availability of the Dynawo launcher in the system's executable path.

    This function calls an external utility to verify if the specified Dynawo launcher
    can be found and executed by the system. If the launcher is not found or is not
    executable, an OSError is caught, logged, and the program exits.

    Parameters
    ----------
    dynawo_launcher_name: str
        The name or path of the Dynawo launcher to check.
    """
    _LOGGER.info(f"Checking Dynawo launcher availability: {dynawo_launcher_name}")
    try:
        # Calls the launcher check function from the sanity_checks module.
        system_checks.check_launchers(dynawo_launcher_name)
        _LOGGER.debug(f"Dynawo launcher '{dynawo_launcher_name}' is available.")
    except OSError as e:
        # If an OSError occurs (due to missing launchers), logs it and exits.
        _LOGGER.critical(f"Dynawo launcher check failed: {e}")
        sys.exit(1)

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
from pathlib import Path

from dycov.logging.logging import dycov_logging
from dycov.sanity_checks import system_checks


def get_dynawo_launcher_name(p: argparse.ArgumentParser, args: argparse.Namespace) -> str:
    """
    Determines the name or path of the Dynawo launcher.

    Parameters
    ----------
    p : argparse.ArgumentParser
        The argument parser.
    args : argparse.Namespace
        The parsed command-line arguments.

    Returns
    -------
    str
        The name or path of the Dynawo launcher.
    """
    # Attempt to get the launcher from the arguments.
    dwo_launcher_name = getattr(args, "dwo_launcher", None)

    if not dwo_launcher_name:
        # If no launcher is provided, use the default name based on the operating system.
        dwo_launcher_name = "dynawo.cmd" if os.name == "nt" else "dynawo.sh"

        # If the default launcher is not found in the system PATH
        # and the command is not 'anonymize' (which doesn't need it), show an error.
        if shutil.which(dwo_launcher_name) is None and args.command != "anonymize":
            p.error(
                "The default Dynawo launcher has not been found, please "
                "provide a correct path using the -l argument."
            )
            p.print_help()
            # In a real script, you might want sys.exit(1) here
            # to terminate execution if the launcher is essential and not found.

    return dwo_launcher_name


def check_dynawo_launcher_availability(dwo_launcher_name: str) -> None:
    """
    Checks the availability of required system launchers.

    Parameters
    ----------
    dwo_launcher_name : str
        The name or path of the Dynawo launcher.
    """
    try:
        # Calls the launcher check function from the sanity_checks module.
        system_checks.check_launchers(dwo_launcher_name)
    except OSError as e:
        # If an OSError occurs (due to missing launchers), logs it and exits.
        dycov_logging.get_logger("Launchers").error(e)
        exit(1)

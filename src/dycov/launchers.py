#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil
from pathlib import Path

# Import functions from the new modules
from dycov.cli.cli_parsers import setup_cli_parsers
from dycov.cli.command_handlers import (
    handle_anonymize_command,
    handle_compile_command,
    handle_generate_command,
    handle_performance_command,
    handle_validate_command,
)
from dycov.cli.utils import check_dynawo_launcher_availability, get_dynawo_launcher_name
from dycov.core import initialization
from dycov.logging.logging import dycov_logging


def dycov() -> None:
    """
    Main function for the dycov command-line interface.
    Parses arguments and dispatches to appropriate subcommands.
    """
    # Set up the main argument parser and its subparsers.
    parser = setup_cli_parsers()
    args = parser.parse_args()

    # If no command is provided, show an error and help message.
    if args.command is None:
        parser.error("Please provide an additional command.")
        parser.print_help()
        return

    # Get the Dynawo launcher name.
    # Not all operations require the Dynawo launcher (e.g., 'anonymize').
    dwo_launcher_name = get_dynawo_launcher_name(parser, args)

    dwo_launcher = None
    if args.command != "anonymize":
        # Check for launcher availability and initialize if not 'anonymize'.
        check_dynawo_launcher_availability(dwo_launcher_name)
        dwo_launcher = Path(shutil.which(dwo_launcher_name)).resolve()
        initialization.init(dwo_launcher, args.debug)
    elif args.debug:
        # If it's 'anonymize' but debug is required, initialize logging.
        # This is necessary because anonymize doesn't go through _get_dynawo_launcher
        # which is where dycov_logging is usually initialized.
        dycov_logging.init_logging(args.debug)

    # Dispatch to the appropriate command handler.
    if args.command == "validate":
        handle_validate_command(parser, args, dwo_launcher)
    elif args.command == "generate":
        handle_generate_command(parser, args, dwo_launcher)
    elif args.command == "compile":
        handle_compile_command(parser, args, dwo_launcher)
    elif args.command == "performance":
        handle_performance_command(parser, args, dwo_launcher)
    elif args.command == "anonymize":
        handle_anonymize_command(parser, args)

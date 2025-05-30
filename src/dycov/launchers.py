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
from dycov.core.initialization import DycovInitializer  # Import the new class
from dycov.logging.logging import dycov_logging


class DycovCLI:
    """
    Manages the command-line interface for the DYCOV tool.
    Parses arguments, handles common initialization steps, and dispatches
    commands to appropriate handlers.
    """

    def __init__(self):
        """
        Initializes the DycovCLI, creating an instance of the DycovInitializer.
        """
        self.initializer = DycovInitializer()
        self.logger = dycov_logging.get_logger("CLI")

    def dycov(self) -> None:
        """
        Main entry point for the dycov command-line interface.
        It parses command-line arguments, performs necessary initializations,
        and dispatches to the relevant command handler functions.
        """
        # Set up the main argument parser and its subparsers.
        parser = setup_cli_parsers()
        args = parser.parse_args()

        # If no command is provided, display an error and the help message.
        if args.command is None:
            parser.error("Please provide a command. Use 'dycov --help' for available commands.")
            return

        dynawo_launcher_path = None

        # Determine Dynawo launcher availability and initialize components based on the command.
        # The 'anonymize' command does not require a Dynawo launcher.
        if args.command != "anonymize":
            dynawo_launcher_name = get_dynawo_launcher_name(parser, args)
            check_dynawo_launcher_availability(dynawo_launcher_name)
            dynawo_launcher_path = Path(shutil.which(dynawo_launcher_name)).resolve()
            self.initializer.init(dynawo_launcher_path, args.debug)
        elif args.debug:
            # For 'anonymize' with debug mode, initialize logging as it bypasses the full 'init'.
            dycov_logging.init_logging(args.debug)
            self.logger.info("Debug mode enabled for anonymize command.")

        # Dispatch the command to the appropriate handler function.
        self._dispatch_command(parser, args, dynawo_launcher_path)

    def _dispatch_command(self, parser, args, dynawo_launcher_path: Path):
        """
        Dispatches the parsed command to its respective handler function.

        Parameters
        ----------
        parser : argparse.ArgumentParser
            The main argument parser.
        args : argparse.Namespace
            Parsed command-line arguments.
        dynawo_launcher_path : Path
            Resolved path to the Dynawo launcher executable, if required.
        """
        if args.command == "validate":
            handle_validate_command(parser, args, dynawo_launcher_path)
        elif args.command == "generate":
            handle_generate_command(parser, args, dynawo_launcher_path)
        elif args.command == "compile":
            handle_compile_command(parser, args, dynawo_launcher_path)
        elif args.command == "performance":
            handle_performance_command(parser, args, dynawo_launcher_path)
        elif args.command == "anonymize":
            handle_anonymize_command(parser, args)
        else:
            # This case should ideally not be reached due to argparse configuration,
            # but it serves as a safeguard.
            self.logger.error(f"Unknown command: {args.command}")
            parser.print_help()


# Exposed function for the command-line entry point
def dycov():
    """
    Entry point for the DYCOV command-line interface.
    Instantiates and runs the DycovCLI.
    """
    cli = DycovCLI()
    cli.dycov()

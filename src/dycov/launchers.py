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
from typing import Optional

# Import functions from the new modules
from dycov.cli.cli_parsers import setup_cli_parsers
from dycov.cli.command_handlers import (
    handle_anonymize_command,
    handle_compile_command,
    handle_generate_command,
    handle_generate_envelopes_command,
    handle_performance_command,
    handle_validate_command,
)
from dycov.cli.utils import check_dynawo_launcher_availability, get_dynawo_launcher_name
from dycov.core.initialization import DycovInitializer
from dycov.logging.logging import dycov_logging


class DycovCLI:
    """Manages the command-line interface for the DYCOV tool.

    Parses arguments, handles common initialization steps, and dispatches
    commands to appropriate handlers.
    """

    def __init__(self):
        """Initializes the DycovCLI, creating an instance of the DycovInitializer."""
        self.initializer = DycovInitializer()
        self.logger = dycov_logging.get_logger("DycovCLI")

    def dycov(self) -> int:
        """Main entry point for the dycov command-line interface.

        It parses command-line arguments, performs necessary initializations,
        and dispatches to the relevant command handler functions.
        """
        self.logger.info("Starting DYCOV CLI.")
        # Set up the main argument parser and its subparsers.
        parser = setup_cli_parsers()
        args = parser.parse_args()

        # If no command is provided, display an error and the help message.
        if args.command is None:
            self.logger.error(
                "Please provide a command. Use 'dycov --help' for available commands."
            )
            parser.error("Please provide a command. Use 'dycov --help' for available commands.")
            return 1

        return self._execute_command(parser, args)

    def _execute_command(self, parser, args) -> int:
        """Executes the given command after handling initialization steps.

        Parameters
        ----------
        parser : argparse.ArgumentParser
            The main argument parser.
        args : argparse.Namespace
            Parsed command-line arguments.
        """
        dynawo_launcher_path: Optional[Path] = None

        # Determine Dynawo launcher availability and initialize components.
        # The 'anonymize' command does not require a Dynawo launcher.
        # The 'generateEnvelopes' command does not require a Dynawo launcher.
        simple_commands = ["anonymize", "generateEnvelopes"]
        if args.command not in simple_commands:
            dynawo_launcher_name = get_dynawo_launcher_name(parser, args)
            check_dynawo_launcher_availability(dynawo_launcher_name)
            dynawo_launcher_path = Path(shutil.which(dynawo_launcher_name)).resolve()
            self.logger.info(f"Dynawo launcher path resolved to: {dynawo_launcher_path}")
        elif args.debug:
            # For 'anonymize' with debug mode, initialize logging as it
            # bypasses the full 'init'.
            dycov_logging.init_logging(args.debug)
            self.logger.info("Debug mode enabled for anonymize command.")

        # Initialize core DYCOV components
        self.initializer.init(dynawo_launcher_path, args.debug)
        self.logger.debug("DycovInitializer completed initialization.")

        # Dispatch the command to the appropriate handler function.
        return self._dispatch_command(parser, args, dynawo_launcher_path)

    def _dispatch_command(self, parser, args, dynawo_launcher_path: Optional[Path]) -> int:
        """Dispatches the parsed command to its respective handler function.

        Parameters
        ----------
        parser : argparse.ArgumentParser
            The main argument parser.
        args : argparse.Namespace
            Parsed command-line arguments.
        dynawo_launcher_path : Path
            Resolved path to the Dynawo launcher executable, if required.
        """
        self.logger.info(f"Dispatching command: {args.command}")
        if args.command == "generateEnvelopes":
            ret = handle_generate_envelopes_command(parser, args, dynawo_launcher_path)
        elif args.command == "validate":
            ret = handle_validate_command(parser, args, dynawo_launcher_path)
        elif args.command == "generate":
            ret = handle_generate_command(parser, args, dynawo_launcher_path)
        elif args.command == "compile":
            ret = handle_compile_command(parser, args, dynawo_launcher_path)
        elif args.command == "performance":
            ret = handle_performance_command(parser, args, dynawo_launcher_path)
        elif args.command == "anonymize":
            ret = handle_anonymize_command(parser, args)
        else:
            # This case should ideally not be reached due to argparse
            # configuration, but it serves as a safeguard.
            self.logger.error(f"Unknown command: {args.command}")
            parser.print_help()
            ret = 1
        return ret


def dycov():
    """Entry point for the DYCOV command-line interface.

    Instantiates and runs the DycovCLI.
    """
    cli = DycovCLI()
    return cli.dycov()

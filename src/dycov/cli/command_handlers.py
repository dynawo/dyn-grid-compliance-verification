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
import time
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import ELECTRIC_PERFORMANCE, MODEL_VALIDATION
from dycov.core.input_template import create_input_template
from dycov.core.validation import Validation
from dycov.curves import anonymizer
from dycov.dynawo import prepare_tool
from dycov.logging.logging import dycov_logging


def _compile_dynawo_models(dwo_launcher: Path, dynawo_model: str, force: bool) -> None:
    # Calls the Dynawo pre-compilation function.
    prepare_tool.precompile(dwo_launcher, dynawo_model, force=force)


def _generate_input(dwo_launcher: Path, target: Path, topology: str, validation: str) -> None:
    # Calls the function to create the Dynawo input template.
    create_input_template(dwo_launcher, target, topology, validation)


def _performance_verification(
    dwo_launcher: Path,
    output_dir: Path,
    producer_model: Path,
    producer_curves: Path,
    user_pcs: str,
    only_dtr: bool,
    testing: bool,
) -> int:
    # Initializes the execution parameters for performance verification.
    ep = Parameters(
        dwo_launcher,
        producer_model,
        producer_curves,
        None,
        user_pcs,
        output_dir,
        only_dtr,
        verification_type=ELECTRIC_PERFORMANCE,
    )

    # Checks if the parameters are valid.
    if ep.is_valid():
        t0 = time.monotonic()  # Marks the start time to measure duration.
        # Retrieves parallelization configuration from the config file.
        use_parallel = config.get_boolean("Global", "parallel_pcs_validation", False)
        num_processes = config.get_int("Global", "parallel_num_processes", 4)
        md = Validation(ep)  # Creates an instance of the Validation class.
        md.set_testing(testing)  # Configures test mode.
        # Executes the validation, with or without parallelization.
        md.validate(use_parallel=use_parallel, num_processes=num_processes)
        # Logs the total execution time for the verification.
        dycov_logging.get_logger("Launchers").debug(
            f"Performance Verification time {time.monotonic() - t0}s"
            f" ({'parallel' if use_parallel else 'sequential'})",
        )
    else:
        return -1  # Returns -1 if parameters are not valid, indicating an error.

    return 0  # Returns 0 if the verification completed successfully.


def _model_validation(
    dwo_launcher: Path,
    output_dir: Path,
    producer_model: Path,
    producer_curves: Path,
    reference_curves: Path,
    user_pcs: str,
    only_dtr: bool,
    testing: bool,
) -> int:
    # Initializes the execution parameters for model validation.
    ep = Parameters(
        dwo_launcher,
        producer_model,
        producer_curves,
        reference_curves,
        user_pcs,
        output_dir,
        only_dtr,
        verification_type=MODEL_VALIDATION,
    )

    # Checks if all necessary parameters for validation are complete.
    if not ep.is_complete():
        return -1  # Returns -1 if parameters are not complete.

    t0 = time.monotonic()  # Marks the start time.
    # Retrieves parallelization configuration from the config file.
    use_parallel = config.get_boolean("Global", "parallel_pcs_validation", False)
    num_processes = config.get_int("Global", "parallel_num_processes", 4)
    md = Validation(ep)  # Creates an instance of the Validation class.
    md.set_testing(testing)  # Configures test mode.
    # Executes the validation.
    md.validate(use_parallel=use_parallel, num_processes=num_processes)
    # Logs the total execution time for the validation.
    dycov_logging.get_logger("Launchers").debug(
        f"Model Validation time {time.monotonic() - t0}s"
        f" ({'parallel' if use_parallel else 'sequential'})",
    )
    return 0  # Returns 0 if the validation completed successfully.


def handle_anonymize_command(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """
    Handles the 'anonymize' command, generating new curves from given ones.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The argument parser.
    args : argparse.Namespace
        Parsed command-line arguments.
    """
    # Verify that the necessary arguments for anonymization are provided.
    if args.producer_curves is None and args.results_path is None:
        parser.error(
            "Missing arguments.\nFor the anonymize command, the producer_curves or the "
            "results_path argument is required."
        )
        parser.print_help()

    # Determine the path for producer curves if provided.
    producer_curves = Path(args.producer_curves) if args.producer_curves else None
    # Determine the path for results if provided.
    results_path = Path(args.results_path) if args.results_path else None

    # Define the output directory. If not specified, use a default directory.
    if args.output_dir is None:
        output_dir = Path(producer_curves.parent / "Anonymize_Results") if producer_curves else Path("Anonymize_Results")
    else:
        output_dir = Path(args.output_dir)

    # Call the curve anonymization function.
    anonymizer.anonymize(output_dir, args.noisestd, args.frequency, results_path, producer_curves)


def handle_compile_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    """
    Handles the 'compile' command, compiling custom Modelica models.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The argument parser.
    args : argparse.Namespace
        Parsed command-line arguments.
    dwo_launcher : Path
        Path to the Dynawo launcher.
    """
    # Get the Dynawo model name, if specified.
    dynawo_model = args.dynawo_model if args.dynawo_model else None
    # Call the private function to compile the models.
    _compile_dynawo_models(dwo_launcher, dynawo_model, args.force)


def handle_generate_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    """
    Handles the 'generate' command, creating necessary input files.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The argument parser.
    args : argparse.Namespace
        Parsed command-line arguments.
    dwo_launcher : Path
        Path to the Dynawo launcher.
    """
    # Verify that the required arguments for 'generate' are present.
    if args.output_dir is None or args.topology is None or args.validation is None:
        parser.error("Missing arguments.\nTry 'dycov generate -h' for more information.")
        parser.print_help()
        return

    # Convert paths and arguments to the correct types.
    output_dir = Path(args.output_dir)
    topology = args.topology
    validation = args.validation

    # Call the private function to generate the input files.
    _generate_input(dwo_launcher, output_dir, topology, validation)


def handle_performance_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    """
    Handles the 'performance' command, running electric performance verification.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The argument parser.
    args : argparse.Namespace
        Parsed command-line arguments.
    dwo_launcher : Path
        Path to the Dynawo launcher.
    """
    user_pcs = args.pcs
    producer_model = None
    producer_curves = None
    output_dir = None

    # Determine the producer's model and/or curves, and the output directory.
    if args.producer_model:
        producer_model = Path(args.producer_model)
        output_dir = Path(args.output_dir) if args.output_dir else producer_model.parent / "Results"
    elif args.producer_curves:
        producer_curves = Path(args.producer_curves)
        output_dir = Path(args.output_dir) if args.output_dir else producer_curves.parent / "Results"

    # If neither model nor curves are provided, show an error.
    if not producer_model and not producer_curves:
        parser.error("Missing arguments.\nTry 'dycov performance -h' for more information.")
        parser.print_help()
        return

    # Call the private function to perform the performance verification.
    result_code = _performance_verification(
        dwo_launcher,
        output_dir,
        producer_model,
        producer_curves,
        user_pcs,
        args.only_dtr,
        args.testing,
    )
    # If the verification is not successful, show an error.
    if result_code != 0:
        parser.error("It is not possible to find the producer model or the producer curves to validate")
        parser.print_help()


def handle_validate_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    """
    Handles the 'validate' command, running RMS model validation.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The argument parser.
    args : argparse.Namespace
        Parsed command-line arguments.
    dwo_launcher : Path
        Path to the Dynawo launcher.
    """
    user_pcs = args.pcs
    producer_model = None
    producer_curves = None
    reference_curves = None
    output_dir = None

    # Determine the producer's model, producer's curves, and reference curves.
    if args.producer_model:
        producer_model = Path(args.producer_model)
        output_dir = Path(args.output_dir) if args.output_dir else producer_model.parent / "Results"
    elif args.producer_curves:
        producer_curves = Path(args.producer_curves)
        output_dir = Path(args.output_dir) if args.output_dir else producer_curves.parent / "Results"

    if args.reference_curves:
        reference_curves = Path(args.reference_curves)

    # If essential arguments are missing, show an error.
    if (not producer_model and not producer_curves) or not reference_curves:
        parser.error("Missing arguments.\nTry 'dycov validate -h' for more information.")
        parser.print_help()
        return

    # Call the private function to perform the model validation.
    result_code = _model_validation(
        dwo_launcher,
        output_dir,
        producer_model,
        producer_curves,
        reference_curves,
        user_pcs,
        args.only_dtr,
        args.testing,
    )
    # If the validation is not successful, show an error.
    if result_code != 0:
        parser.error(
            "It is not possible to find the producer model or the producer curves "
            "to validate. You MUST provide both."
        )
        parser.print_help()
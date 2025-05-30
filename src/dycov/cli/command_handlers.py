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
from typing import Optional

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import ELECTRIC_PERFORMANCE, MODEL_VALIDATION
from dycov.core.input_template import InputTemplateGenerator
from dycov.core.validation import Validation
from dycov.curves import anonymizer
from dycov.curves.dynawo import prepare_tool
from dycov.logging.logging import dycov_logging


def _run_verification(
    dwo_launcher: Path,
    output_dir: Path,
    producer_model: Optional[Path],
    producer_curves: Optional[Path],
    reference_curves: Optional[Path],
    user_pcs: str,
    only_dtr: bool,
    testing: bool,
    verification_type: int,
) -> int:
    """Initializes and runs a model validation or performance verification.

    This is a centralized function to handle both `_performance_verification` and
    `_model_validation` logic, reducing code duplication.

    Parameters
    ----------
    dwo_launcher: Path
        Path to the Dynawo launcher.
    output_dir: Path
        User output directory.
    producer_model: Optional[Path]
        Producer Model directory, if applicable.
    producer_curves: Optional[Path]
        Producer curves directory, if applicable.
    reference_curves: Optional[Path]
        Reference curves directory, if applicable.
    user_pcs: str
        Individual Performance Checking Sheet (PCS) to validate.
    only_dtr: bool
        Option to validate a model using only the PCS defined in the DTR.
    testing: bool
        Flag indicating if the tool is in testing mode.
    verification_type: int
        Type of verification to perform (ELECTRIC_PERFORMANCE or MODEL_VALIDATION).

    Returns
    -------
    int
        0 if the verification completed successfully, -1 otherwise.
    """
    ep = Parameters(
        launcher_dwo=dwo_launcher,
        producer_model=producer_model,
        producer_curves_path=producer_curves,
        reference_curves_path=reference_curves,
        selected_pcs=user_pcs,
        output_dir=output_dir,
        only_dtr=only_dtr,
        verification_type=verification_type,
    )

    # Determine if the execution parameters are valid or complete based on the verification type.
    is_ready = ep.is_valid() if verification_type == ELECTRIC_PERFORMANCE else ep.is_complete()

    if not is_ready:
        return -1

    t0 = time.monotonic()
    use_parallel = config.get_boolean("Global", "parallel_pcs_validation", False)
    num_processes = config.get_int("Global", "parallel_num_processes", 4)

    md = Validation(ep)
    md.set_testing(testing)
    md.validate(use_parallel=use_parallel, num_processes=num_processes)

    logger_name = "Launchers"
    verification_name = (
        "Performance Verification"
        if verification_type == ELECTRIC_PERFORMANCE
        else "Model Validation"
    )
    parallel_status = "parallel" if use_parallel else "sequential"
    dycov_logging.get_logger(logger_name).debug(
        f"{verification_name} time {time.monotonic() - t0}s ({parallel_status})"
    )

    return 0


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
        return

    # Determine the path for producer curves if provided.
    producer_curves = Path(args.producer_curves) if args.producer_curves else None
    # Determine the path for results if provided.
    results_path = Path(args.results_path) if args.results_path else None

    # Define the output directory. If not specified, use a default directory.
    if args.output_dir is None:
        output_dir = (
            Path(producer_curves.parent / "Anonymize_Results")
            if producer_curves
            else Path("Anonymize_Results")
        )
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
    # Calls the Dynawo pre-compilation function.
    prepare_tool.precompile(dwo_launcher, dynawo_model, force=args.force)


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

    # Calls the function to create the Dynawo input template.
    generator = InputTemplateGenerator()
    generator.create_input_template(dwo_launcher, output_dir, topology, validation)


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
    producer_model: Optional[Path] = None
    producer_curves: Optional[Path] = None
    output_dir: Optional[Path] = None

    # Determine the producer's model and/or curves, and the output directory.
    if args.producer_model:
        producer_model = Path(args.producer_model)
        output_dir = (
            Path(args.output_dir) if args.output_dir else producer_model.parent / "Results"
        )
    elif args.producer_curves:
        producer_curves = Path(args.producer_curves)
        output_dir = (
            Path(args.output_dir) if args.output_dir else producer_curves.parent / "Results"
        )

    # If neither model nor curves are provided, show an error.
    if not producer_model and not producer_curves:
        parser.error("Missing arguments.\nTry 'dycov performance -h' for more information.")
        parser.print_help()
        return

    # Call the generic verification function.
    result_code = _run_verification(
        dwo_launcher=dwo_launcher,
        output_dir=output_dir,
        producer_model=producer_model,
        producer_curves=producer_curves,
        reference_curves=None,  # Not applicable for performance verification
        user_pcs=args.pcs,
        only_dtr=args.only_dtr,
        testing=args.testing,
        verification_type=ELECTRIC_PERFORMANCE,
    )

    if result_code != 0:
        parser.error(
            "It is not possible to find the producer model or the producer curves to validate"
        )
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
    producer_model: Optional[Path] = None
    producer_curves: Optional[Path] = None
    reference_curves: Optional[Path] = None
    output_dir: Optional[Path] = None

    # Determine the producer's model, producer's curves, and reference curves.
    if args.producer_model:
        producer_model = Path(args.producer_model)
        output_dir = (
            Path(args.output_dir) if args.output_dir else producer_model.parent / "Results"
        )
    elif args.producer_curves:
        producer_curves = Path(args.producer_curves)
        output_dir = (
            Path(args.output_dir) if args.output_dir else producer_curves.parent / "Results"
        )

    if args.reference_curves:
        reference_curves = Path(args.reference_curves)

    # If essential arguments are missing, show an error.
    if (not producer_model and not producer_curves) or not reference_curves:
        parser.error("Missing arguments.\nTry 'dycov validate -h' for more information.")
        parser.print_help()
        return

    # Call the generic verification function.
    result_code = _run_verification(
        dwo_launcher=dwo_launcher,
        output_dir=output_dir,
        producer_model=producer_model,
        producer_curves=producer_curves,
        reference_curves=reference_curves,
        user_pcs=args.pcs,
        only_dtr=args.only_dtr,
        testing=args.testing,
        verification_type=MODEL_VALIDATION,
    )

    if result_code != 0:
        parser.error(
            "It is not possible to find the producer model or the producer curves "
            "to validate. You MUST provide both."
        )
        parser.print_help()

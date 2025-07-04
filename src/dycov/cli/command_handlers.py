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

_LOGGER = dycov_logging.get_logger("CommandHandlers")


def handle_validate_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    """Handles the 'validate' command.

    Initializes and runs a model validation based on the provided arguments.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The argument parser instance.
    args: argparse.Namespace
        Parsed command-line arguments.
    dwo_launcher: Path
        Path to the Dynawo launcher.
    """
    _LOGGER.info("Handling 'validate' command.")
    producer_model: Optional[Path] = None
    producer_curves: Optional[Path] = None
    reference_curves: Optional[Path] = None
    output_dir: Optional[Path] = None

    if args.model:
        producer_model = Path(args.model)
        output_dir = args.output if args.output else producer_model.parent / "Results"
        _LOGGER.debug(f"Producer model: {producer_model}")
    elif args.curves:
        producer_curves = Path(args.curves)
        output_dir = args.output if args.output else producer_curves.parent / "Results"
        _LOGGER.debug(f"Producer curves: {producer_curves}")

    if args.reference:
        reference_curves = Path(args.reference)
        _LOGGER.debug(f"Reference curves: {reference_curves}")

    if (not producer_model and not producer_curves) or not reference_curves:
        _LOGGER.error("Missing arguments for 'validate' command.")
        parser.error("Missing arguments. Try 'dycov validate -h' for more information.")
        return

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
        _LOGGER.critical("Validation failed. Check logs for details.")
        parser.error(
            "It is not possible to find the producer model or the producer curves. " "Exiting."
        )


def handle_performance_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    """Handles the 'performance' command.

    Analyzes the performance of a Dynawo model or its results.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The argument parser instance.
    args: argparse.Namespace
        Parsed command-line arguments.
    dwo_launcher: Path
        Path to the Dynawo launcher.
    """
    _LOGGER.info("Handling 'performance' command.")
    producer_model: Optional[Path] = None
    producer_curves: Optional[Path] = None
    output_dir: Optional[Path] = None

    if args.model:
        producer_model = Path(args.model)
        output_dir = args.output if args.output else producer_model.parent / "Results"
        _LOGGER.debug(f"Producer model: {producer_model}")
    elif args.curves:
        producer_curves = Path(args.curves)
        output_dir = args.output if args.output else producer_curves.parent / "Results"
        _LOGGER.debug(f"Producer curves: {producer_curves}")
    else:
        _LOGGER.error("Missing model or output directory for 'performance' command.")
        parser.error("Missing arguments. Try 'dycov performance -h' for more information.")
        return

    result_code = _run_verification(
        dwo_launcher=dwo_launcher,
        output_dir=output_dir,
        producer_model=producer_model,
        producer_curves=producer_curves,
        reference_curves=None,  # Not used for performance analysis
        user_pcs=args.pcs,
        only_dtr=args.only_dtr,
        testing=args.testing,
        verification_type=ELECTRIC_PERFORMANCE,
    )

    if result_code != 0:
        _LOGGER.critical("Performance analysis failed. Check logs for details.")
        parser.error(
            "It is not possible to find the producer model or the producer curves. " "Exiting."
        )


def handle_generate_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    """Handles the 'generate' command.

    Creates necessary input files through a guided process.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The argument parser instance.
    args: argparse.Namespace
        Parsed command-line arguments.
    dwo_launcher: Path
        Path to the Dynawo launcher.
    """
    _LOGGER.info("Handling 'generate' command.")
    try:
        # Initialize Parameters for the tool
        params = Parameters()
        params.init_tool(dwo_launcher)
        params.set_topology_path(args.topology)
        params.set_validation_path(args.validation)
        params.set_output_path(args.output)
        _LOGGER.debug("Parameters initialized for generate command.")

        # Generate input templates
        generator = InputTemplateGenerator(params)
        generator.generate_templates()
        _LOGGER.info("Input files generated successfully.")
    except Exception as e:
        _LOGGER.exception(f"Error generating input files: {e}")
        parser.error(f"Failed to generate input files: {e}")


def handle_compile_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> None:
    """Handles the 'compile' command.

    Compiles custom Modelica models.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The argument parser instance.
    args: argparse.Namespace
        Parsed command-line arguments.
    dwo_launcher: Path
        Path to the Dynawo launcher.
    """
    _LOGGER.info("Handling 'compile' command.")
    model_name: Optional[str] = args.dynamic_model if args.dynamic_model else None
    force_recompile: bool = args.force

    try:
        if prepare_tool.precompile(dwo_launcher, model_name, force_recompile):
            _LOGGER.info("Model compilation aborted by user.")
            print("Compilation aborted by user.")
        else:
            _LOGGER.info("Model(s) compiled successfully.")
            print("Compilation finished successfully.")
    except Exception as e:
        _LOGGER.exception(f"Error compiling models: {e}")
        parser.error(f"Failed to compile models: {e}")


def handle_anonymize_command(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Handles the 'anonymize' command.

    Generates a new set of curves with generic variable names and optional noise.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The argument parser instance.
    args: argparse.Namespace
        Parsed command-line arguments.
    """
    _LOGGER.info("Handling 'anonymize' command.")
    try:
        anonymizer.anonymize(
            output_folder=args.output,
            noisestd=args.noisestd,
            frequency=args.frequency,
            results=args.results,
            curves_folder=args.curves,
        )
        _LOGGER.info("Anonymization completed successfully.")
    except Exception as e:
        _LOGGER.exception(f"Error during anonymization: {e}")
        parser.error(f"Failed to anonymize curves: {e}")


def _run_verification(
    dwo_launcher: Path,
    output_dir: Path,
    producer_model: Optional[Path],
    producer_curves: Optional[Path],
    reference_curves: Optional[Path],
    user_pcs: bool,
    only_dtr: bool,
    testing: bool,
    verification_type: int,
    validation_file: Optional[Path] = None,
    validation_type: Optional[str] = None,
) -> int:
    """Initializes and runs a model validation or performance verification.

    This is a centralized function to handle both `_performance_verification`
    and `_model_validation` logic, reducing code duplication.

    Parameters
    ----------
    dwo_launcher: Path
        Path to the Dynawo launcher.
    output_dir: Path
        User output directory.
    producer_model: Optional[Path]
        Producer Model directory, if applicable.
    producer_curves: Optional[Path]
        Producer Curves directory, if applicable.
    reference_curves: Optional[Path]
        Reference Curves directory, if applicable.
    user_pcs: bool
        Flag indicating if PCS are included.
    only_dtr: bool
        If True, only create DTR files without running simulation.
    testing: bool
        If True, run in testing mode.
    verification_type: int
        Type of verification (MODEL_VALIDATION or ELECTRIC_PERFORMANCE).

    Returns
    -------
    int
        Result code of the verification (0 for success, non-zero for failure).
    """
    _LOGGER.info(f"Running verification of type: {verification_type}")
    try:
        # Initialize Parameters for the tool
        params = Parameters(
            launcher_dwo=dwo_launcher,
            producer_model=producer_model,
            producer_curves_path=producer_curves,
            reference_curves_path=reference_curves,
            selected_pcs=user_pcs,
            output_dir=output_dir,
            only_dtr=only_dtr,
            verification_type=verification_type,
        )

        # Determine if the execution parameters are valid or complete based on the
        # verification type.
        is_ready = (
            params.is_valid()
            if verification_type == ELECTRIC_PERFORMANCE
            else params.is_complete()
        )

        if not is_ready:
            return -1

        use_parallel = config.get_boolean("Global", "parallel_pcs_validation", False)
        num_processes = config.get_int("Global", "parallel_num_processes", 4)

        # Initialize the Validation object
        validation = Validation(params)
        validation.set_testing(testing)

        start_time = time.time()
        validation.validate(use_parallel=use_parallel, num_processes=num_processes)
        end_time = time.time()

        parallel_status = "parallel" if use_parallel else "sequential"
        verification_name = (
            "Performance Verification"
            if verification_type == ELECTRIC_PERFORMANCE
            else "Model Validation"
        )
        _LOGGER.info(
            f"{verification_name} completed in {end_time - start_time:.2f} seconds."
            f" ({parallel_status})"
        )
        return 0
    except Exception as e:
        _LOGGER.exception(f"Error during verification: {e}")
        return 1

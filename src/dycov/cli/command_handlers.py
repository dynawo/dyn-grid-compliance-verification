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
import logging
import time
from pathlib import Path
from typing import Optional

from dycov.configuration.cfg import config
from dycov.core.global_variables import ELECTRIC_PERFORMANCE, MODEL_VALIDATION
from dycov.core.input_template import InputTemplateGenerator
from dycov.curves import anonymizer
from dycov.curves.dynawo.tooling import prepare_tool
from dycov.files import manage_files
from dycov.gfm.generator import GFMGeneration
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging
from dycov.validate.parameters import ValidationParameters
from dycov.validate.validation import Validation


def handle_generate_envelopes_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> int:
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
    dycov_logging.get_logger("CommandHandlers").info("Handling 'generateEnvelopes' command.")
    producer_ini: Optional[Path] = None
    output_dir: Optional[Path] = None

    emt = args.emt
    if args.producer_ini:
        producer_ini = Path(args.producer_ini)
        output_dir = producer_ini.parent / "Results" if args.output is None else Path(args.output)

    if not producer_ini:
        dycov_logging.get_logger("CommandHandlers").error(
            "Missing arguments for 'generateEnvelopes' command."
        )
        parser.error("Missing arguments. Try 'dycov generateEnvelopes -h' for more information.")
        return

    result_code = _generate_envelopes(
        dwo_launcher=dwo_launcher,
        output_dir=output_dir,
        producer_ini=producer_ini,
        emt=emt,
        user_pcs=args.pcs,
        only_dtr=args.only_dtr,
    )

    if result_code == -1:
        dycov_logging.get_logger("CommandHandlers").critical(
            "Validation failed. Check logs for details."
        )
        parser.error(
            "It is not possible to find the producer model or the producer curves. Exiting."
        )
    return result_code


def handle_validate_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> int:
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
    dycov_logging.get_logger("CommandHandlers").info("Handling 'validate' command.")
    producer_model: Optional[Path] = None
    producer_curves: Optional[Path] = None
    reference_curves: Optional[Path] = None
    output_dir: Optional[Path] = None

    if args.model:
        producer_model = Path(args.model)
        output_dir = args.output if args.output else producer_model.parent / "Results"
        dycov_logging.get_logger("CommandHandlers").debug(f"Producer model: {producer_model}")
    elif args.curves:
        producer_curves = Path(args.curves)
        output_dir = args.output if args.output else producer_curves.parent / "Results"
        dycov_logging.get_logger("CommandHandlers").debug(f"Producer curves: {producer_curves}")

    if args.reference:
        reference_curves = Path(args.reference)
        dycov_logging.get_logger("CommandHandlers").debug(f"Reference curves: {reference_curves}")

    if (not producer_model and not producer_curves) or not reference_curves:
        dycov_logging.get_logger("CommandHandlers").error(
            "Missing arguments for 'validate' command."
        )
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

    if result_code == -1:
        dycov_logging.get_logger("CommandHandlers").critical(
            "Validation failed. Check logs for details."
        )
        parser.error(
            "It is not possible to find the producer model or the producer curves. Exiting."
        )
    return result_code


def handle_performance_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> int:
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
    dycov_logging.get_logger("CommandHandlers").info("Handling 'performance' command.")
    producer_model: Optional[Path] = None
    producer_curves: Optional[Path] = None
    output_dir: Optional[Path] = None

    if args.model:
        producer_model = Path(args.model)
        output_dir = args.output if args.output else producer_model.parent / "Results"
        dycov_logging.get_logger("CommandHandlers").debug(f"Producer model: {producer_model}")
    elif args.curves:
        producer_curves = Path(args.curves)
        output_dir = args.output if args.output else producer_curves.parent / "Results"
        dycov_logging.get_logger("CommandHandlers").debug(f"Producer curves: {producer_curves}")
    else:
        dycov_logging.get_logger("CommandHandlers").error(
            "Missing model or output directory for 'performance' command."
        )
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

    if result_code == -1:
        dycov_logging.get_logger("CommandHandlers").critical(
            "Performance analysis failed. Check logs for details."
        )
        parser.error(
            "It is not possible to find the producer model or the producer curves. Exiting."
        )
    return result_code


def handle_generate_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> int:
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
    dycov_logging.get_logger("CommandHandlers").info("Handling 'generate' command.")
    try:
        # Generate input templates
        generator = InputTemplateGenerator()
        result_code = generator.create_input_template(
            launcher_dwo=dwo_launcher,
            target=Path(args.output),
            topology=args.topology,
            template=args.validation,
        )
        dycov_logging.get_logger("CommandHandlers").info("Input files generated successfully.")
    except Exception as e:
        dycov_logging.get_logger("CommandHandlers").error(f"Error generating input files: {e}")
        parser.error(f"Failed to generate input files: {e}")
        result_code = 1
    return result_code


def handle_compile_command(
    parser: argparse.ArgumentParser, args: argparse.Namespace, dwo_launcher: Path
) -> int:
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
    dycov_logging.get_logger("CommandHandlers").info("Handling 'compile' command.")
    model_name: Optional[str] = args.dynamic_model if args.dynamic_model else None
    force_recompile: bool = args.force

    try:
        if prepare_tool.precompile(dwo_launcher, model_name, force_recompile):
            dycov_logging.get_logger("CommandHandlers").info("Model compilation aborted by user.")
            print("Compilation aborted by user.")
            result_code = 1
        else:
            dycov_logging.get_logger("CommandHandlers").info("Model(s) compiled successfully.")
            print("Compilation finished successfully.")
            result_code = 0
    except Exception as e:
        dycov_logging.get_logger("CommandHandlers").error(f"Error compiling models: {e}")
        parser.error(f"Failed to compile models: {e}")
        result_code = 1
    return result_code


def handle_anonymize_command(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Handles the 'anonymize' command.

    Generates a new set of curves with generic variable names and optional noise.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The argument parser instance.
    args: argparse.Namespace
        Parsed command-line arguments.
    """
    dycov_logging.get_logger("CommandHandlers").info("Handling 'anonymize' command.")
    try:
        anonymizer.anonymize(
            output_folder=Path(args.output),
            noisestd=args.noisestd,
            frequency=args.frequency,
            results=Path(args.results) if args.results else None,
            curves_folder=Path(args.curves) if args.curves else None,
        )
        dycov_logging.get_logger("CommandHandlers").info("Anonymization completed successfully.")
        result_code = 0
    except Exception as e:
        dycov_logging.get_logger("CommandHandlers").error(f"Error during anonymization: {e}")
        parser.error(f"Failed to anonymize curves: {e}")
        result_code = 1
    return result_code


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
    dycov_logging.get_logger("CommandHandlers").info(
        f"Running verification of type: {verification_type}"
    )
    try:
        # Initialize Parameters for the tool
        params = ValidationParameters(
            launcher_dwo=dwo_launcher,
            producer_model=producer_model,
            producer_curves_path=producer_curves,
            reference_curves_path=reference_curves,
            selected_pcs=user_pcs,
            output_dir=output_dir,
            only_dtr=only_dtr,
            verification_type=verification_type,
        )
    except ValueError as e:
        dycov_logging.get_logger("CommandHandlers").error(f"{e}")
        return 1

    try:
        # Determine if the execution parameters are valid or complete based on the
        # verification type.
        is_ready = (
            params.is_valid()
            if verification_type == ELECTRIC_PERFORMANCE
            else params.is_complete()
        )

        if not is_ready:
            return -1

        use_parallel = config.get_boolean("Global", "parallel_pcs_validation", True)
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
        dycov_logging.get_logger("CommandHandlers").info(
            f"{verification_name} completed in {end_time - start_time:.2f} seconds."
            f" ({parallel_status})"
        )

        return 0
    except KeyboardInterrupt:
        dycov_logging.get_logger("CommandHandlers").error("Execution interrupted by user")
        if dycov_logging.get_logger("CommandHandlers").getEffectiveLevel() == logging.DEBUG:
            manage_files.rename_path(params.get_working_dir(), params.get_output_dir())
        else:
            manage_files.remove_dir(params.get_working_dir())
        return 130
    except Exception as e:
        dycov_logging.get_logger("CommandHandlers").error(f"Error during verification: {e}")
        if dycov_logging.get_logger("CommandHandlers").getEffectiveLevel() == logging.DEBUG:
            manage_files.rename_path(params.get_working_dir(), params.get_output_dir())
        else:
            manage_files.remove_dir(params.get_working_dir())
        raise
        return 1


def _generate_envelopes(
    dwo_launcher: Path,
    output_dir: Path,
    producer_ini: Path,
    emt: bool,
    user_pcs: bool,
    only_dtr: bool,
):
    dycov_logging.get_logger("CommandHandlers").info("Running generation of envelopes")
    try:
        params = GFMParameters(
            launcher_dwo=dwo_launcher,
            producer_ini=producer_ini,
            selected_pcs=user_pcs,
            output_dir=output_dir,
            only_dtr=only_dtr,
            emt=emt,
        )

        # Determine if the parameters are valid.
        if not params.is_valid():
            return -1

        use_parallel = config.get_boolean("Global", "parallel_pcs_validation", True)
        num_processes = config.get_int("Global", "parallel_num_processes", 4)

        gfm = GFMGeneration(params)
        start_time = time.time()
        gfm.generate(use_parallel=use_parallel, num_processes=num_processes)
        end_time = time.time()

        dycov_logging.get_logger("CommandHandlers").info(
            f"Generation completed in {end_time - start_time:.2f} seconds."
        )
        return 0
    except Exception as e:
        dycov_logging.get_logger("CommandHandlers").error(f"Error during generation: {e}")
        return 1

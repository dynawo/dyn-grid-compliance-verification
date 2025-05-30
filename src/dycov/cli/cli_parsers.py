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
from importlib.metadata import version
from typing import Optional


def _add_argument(
    parser: argparse.ArgumentParser,
    *args,
    help_msg: str,
    action: Optional[str] = None,
    default: Optional[any] = None,
    arg_type: Optional[type] = None,
    choices: Optional[list] = None,
    nargs: Optional[str] = None,
    is_required: bool = False,  # Renamed from 'required' to avoid conflict and for clarity
) -> None:
    """Helper function to add an argument to a parser, dynamically including only
    non-None parameters and handling 'required' based on argument type (positional vs. optional).
    """
    kwargs = {
        "help": help_msg,
    }

    # Determine if it's an optional argument (starts with '-')
    # 'required' is only valid for optional arguments. Positional arguments are required
    # by default.
    is_optional_arg = any(arg.startswith("-") for arg in args)

    if is_required and is_optional_arg:
        kwargs["required"] = True
    # For positional arguments, 'required' is implicitly True if nargs is not '?' or '*'
    # and should not be explicitly set in add_argument, as it causes a TypeError.
    # We do not add 'required=False' for optional args if is_required is False,
    # as this is the default behavior.

    if action is not None:
        kwargs["action"] = action
    if default is not None:
        kwargs["default"] = default
    if arg_type is not None:
        kwargs["type"] = arg_type
    if choices is not None:
        kwargs["choices"] = choices
    if nargs is not None:
        kwargs["nargs"] = nargs

    parser.add_argument(
        *args,
        **kwargs,
    )


def _add_testing_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the optional --testing argument to the parser."""
    _add_argument(
        parser, "--testing", action="store_true", help_msg=argparse.SUPPRESS, default=False
    )


def _add_launcher_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --dwo_launcher argument to the parser."""
    _add_argument(
        parser,
        "-l",
        "--dwo_launcher",
        is_required=required,
        help_msg="path to the Dynawo launcher",
        default=None,
    )


def _add_output_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --output_dir argument to the parser."""
    _add_argument(
        parser,
        "-o",
        "--output_dir",
        is_required=required,
        help_msg="path to the output directory",
        default=None,
    )


def _add_model_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --producer_model argument to the parser."""
    _add_argument(
        parser,
        "-m",
        "--producer_model",
        is_required=required,
        help_msg="path to the directory containing the producer's RMS model files (DYD, PAR, INI)",
        default=None,
    )


def _add_curves_argument(
    parser: argparse.ArgumentParser, explain: str, required: bool = False
) -> None:
    """Adds the --producer_curves argument to the parser."""
    _add_argument(
        parser,
        "-c",
        "--producer_curves",
        is_required=required,
        help_msg=f"path to the directory containing producer's curves {explain}",
        default=None,
    )


def _add_verification_results_path(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
    """Adds the --results_path argument to the parser."""
    _add_argument(
        parser,
        "-r",
        "--results_path",
        is_required=required,
        help_msg="path to the results directory of a model verification",
        default=None,
    )


def _add_reference_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the --reference_curves argument to the parser."""
    # This is a positional argument, 'required' parameter should not be passed to
    # add_argument for it.
    # 'nargs="?"' makes it optional anyway.
    _add_argument(
        parser,
        "reference_curves",
        nargs="?",
        help_msg="path to the directory containing the reference curves used for validation",
        default=None,
        is_required=False,  # Explicitly set to False, as it's optional positional due to nargs="?"
    )


def _add_pcs_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --pcs argument to the parser."""
    _add_argument(
        parser,
        "-p",
        "--pcs",
        is_required=required,
        help_msg="run only the given Performance Checking Sheet (PCS)",
        default=None,
    )


def _add_topology_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --topology argument to the parser."""
    _add_argument(
        parser,
        "-t",
        "--topology",
        is_required=required,
        help_msg="choice of topology to implement in the DYD file",
        choices=["S", "S+i", "S+Aux", "S+Aux+i", "M", "M+i", "M+Aux", "M+Aux+i"],
        default=None,
    )


def _add_validation_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --validation argument to the parser."""
    _add_argument(
        parser,
        "-v",
        "--validation",
        is_required=required,
        help_msg="choice of processs, performance verification (SM, PPM or BESS) "
        "vs. RMS model validation (PPM or BESS)",
        choices=["performance_SM", "performance_PPM", "model_PPM", "model_BESS"],
        default=None,
    )


def _add_dynamic_model_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --dynawo_model argument to the parser."""
    _add_argument(
        parser,
        "-m",
        "--dynawo_model",
        is_required=required,
        help_msg="XML file describing a custom Modelica model",
        default=None,
    )


def _add_force_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --force argument to the parser."""
    _add_argument(
        parser,
        "-f",
        "--force",
        is_required=required,
        action="store_true",
        help_msg="force the recompilation of all Modelica models (the user's and the tool's own)",
    )


def _add_noise_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --noisestd argument to the parser."""
    _add_argument(
        parser,
        "-n",
        "--noisestd",
        is_required=required,
        arg_type=float,
        help_msg="standard deviation of the noise added to the curves, in pu (recommended range:"
        " [0.01, 0.1])",
    )


def _add_frequency_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --frequency argument to the parser."""
    _add_argument(
        parser,
        "-f",
        "--frequency",
        is_required=required,
        arg_type=float,
        help_msg="cut-off frequency of the filter used for smoothing the noise, in Hz"
        " (default: 3.0, recommended range: [1.0, 5.0])",
        default=3.0,
    )


def _add_debug_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the --debug argument to the parser."""
    _add_argument(
        parser, "-d", "--debug", action="store_true", help_msg="show debug messages", default=False
    )


def _add_only_dtr_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the --only_dtr argument to the parser."""
    _add_argument(
        parser,
        "-od",
        "--only_dtr",
        action="store_true",
        help_msg="run only the official PCS's defined in the DTR "
        "(i.e., ignore any custom defined PCS)",
        default=False,
    )


def _add_version_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the --version argument to the parser."""
    # This one cannot use _add_argument because 'version' is a specific action
    # directly on parser.add_argument, not a generic argument type.
    parser.add_argument("--version", action="version", version=version("dycov"))


def setup_cli_parsers() -> argparse.ArgumentParser:
    """
    Sets up the main argument parser with subparsers for commands.

    Returns
    -------
    argparse.ArgumentParser
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="dycov",
        description="DYnamic COmpliance Verification tool for RMS models",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    _add_version_argument(parser)

    # Subparser for the 'validate' command.
    validate = subparsers.add_parser("validate", help="run the RMS model validation process")
    group = validate.add_mutually_exclusive_group(required=False)
    _add_debug_argument(validate)
    _add_launcher_argument(validate)
    _add_model_argument(group)
    _add_curves_argument(group, explain="(when using curves instead of an RMS model)")
    _add_reference_argument(validate)
    _add_output_argument(validate)
    _add_pcs_argument(validate)
    _add_only_dtr_argument(validate)
    _add_testing_argument(validate)

    # Subparser for the 'performance' command.
    performance = subparsers.add_parser(
        "performance",
        help="run the electric performance verification process",
    )
    _add_debug_argument(performance)
    _add_launcher_argument(performance)
    _add_model_argument(performance)
    _add_curves_argument(
        performance, explain="(if a model is also provided, these are used only for graphing)"
    )
    _add_output_argument(performance)
    _add_pcs_argument(performance)
    _add_only_dtr_argument(performance)
    _add_testing_argument(performance)

    # Subparser for the 'generate' command.
    generate = subparsers.add_parser(
        "generate",
        help="create all the necessary input files through a guided process",
    )
    _add_debug_argument(generate)
    _add_launcher_argument(generate)
    _add_output_argument(generate, required=True)
    _add_topology_argument(generate, required=True)
    _add_validation_argument(generate, required=True)

    # Subparser for the 'compile' command.
    compile_model = subparsers.add_parser(
        "compile",
        help="compile custom Modelica models",
    )
    _add_debug_argument(compile_model)
    _add_launcher_argument(compile_model)
    _add_dynamic_model_argument(compile_model)
    _add_force_argument(compile_model)

    # Subparser for the 'anonymize' command.
    anonymize = subparsers.add_parser(
        "anonymize",
        help="generate a new set of curves from a given one, using generic var names and "
        "with (optional) noise added",
    )
    _add_debug_argument(anonymize)
    _add_curves_argument(anonymize, explain="", required=False)
    _add_output_argument(anonymize)
    _add_noise_argument(anonymize)
    _add_frequency_argument(anonymize)
    _add_verification_results_path(anonymize)

    return parser

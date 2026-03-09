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
from pathlib import Path
from typing import Optional

from dycov.logging.logging import dycov_logging


def setup_cli_parsers() -> argparse.ArgumentParser:
    """Sets up the command-line argument parsers for the DYCOV tool.

    This function defines the main parser and its subparsers for various
    DYCOV commands like validate, performance, generate, compile, and anonymize.

    Returns
    -------
    argparse.ArgumentParser
        The configured argument parser.
    """
    dycov_logging.get_logger("CliParsers").info("Setting up CLI parsers.")
    main_parser = argparse.ArgumentParser(
        prog="dycov",
        description="Dynamic grid Compliance Verification tool.",
        epilog="Use 'dycov <command> --help' for more information on a specific command.",
    )

    # Add global arguments
    main_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {version('dycov')}",
        help="Show program's version number and exit.",
    )
    _add_debug_argument(main_parser)

    # Set up subparsers for different commands
    subparsers = main_parser.add_subparsers(dest="command", help="Available commands")

    _add_generate_envelopes_subparser(subparsers)
    _add_validate_subparser(subparsers)
    _add_performance_subparser(subparsers)
    _add_generate_subparser(subparsers)
    _add_anonymize_subparser(subparsers)

    return main_parser


def _add_argument(
    parser: argparse.ArgumentParser,
    *args,
    help_msg: str,
    action: Optional[str] = None,
    default: Optional[any] = None,
    arg_type: Optional[type] = None,
    choices: Optional[list] = None,
    nargs: Optional[str] = None,
    is_required: bool = False,
) -> None:
    """Helper function to add an argument to a parser, dynamically including only
    non-None parameters and handling 'required' based on argument type (positional
    vs. optional).

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    *args: str
        The argument names (e.g., "-d", "--debug").
    help_msg: str
        The help message for the argument.
    action: Optional[str]
        The action to be taken when this argument is encountered.
    default: Optional[any]
        The default value for the argument if it's not provided.
    arg_type: Optional[type]
        The type to which the command-line argument should be converted.
    choices: Optional[list]
        A container of the allowable values for the argument.
    nargs: Optional[str]
        The number of command-line arguments that should be consumed.
    is_required: bool
        Whether the argument is required.
    """
    kwargs = {"help": help_msg}

    # 'required' is only valid for optional arguments. Positional arguments are
    # required by default unless nargs is '?' or '*'.
    is_optional_arg = any(arg.startswith("-") for arg in args)

    if is_required and is_optional_arg:
        kwargs["required"] = True
    if action:
        kwargs["action"] = action
    if default is not None:
        kwargs["default"] = default
    if arg_type:
        kwargs["type"] = arg_type
    if choices:
        kwargs["choices"] = choices
    if nargs:
        kwargs["nargs"] = nargs

    parser.add_argument(*args, **kwargs)
    dycov_logging.get_logger("CliParsers").debug(
        f"Added argument {args} to parser with help: {help_msg}"
    )


def _add_debug_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--debug' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-d",
        "--debug",
        action="store_true",
        help_msg="Enable debug logging.",
    )


def _add_launcher_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--launcher' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-l",
        "--launcher",
        arg_type=str,
        help_msg=(
            "Dynawo launcher for the tool (e.g., dynawo.sh). If not "
            "provided, the tool will try to find it from the PATH "
            "environment variable."
        ),
    )


def _add_ini_argument(
    parser: argparse.ArgumentParser,
    explain: str = "",
    is_required: bool = False,
) -> None:
    """Adds the '--producer_ini' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    explain: str
        Additional explanation for the help message.
    is_required: bool
        Whether the argument is required.
    """
    help_msg = "producer file describing the physical and control parameters of the installation."
    if explain:
        help_msg += f" {explain}"
    _add_argument(
        parser,
        "-i",
        "--producer_ini",
        arg_type=Path,
        help_msg=help_msg,
        is_required=is_required,
    )


def _add_emt_argument(
    parser: argparse.ArgumentParser,
    explain: str = "",
    is_required: bool = False,
) -> None:
    """Adds the '--emt' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    explain: str
        Additional explanation for the help message.
    is_required: bool
        Whether the argument is required.
    """
    _add_argument(
        parser,
        "-e",
        "--emt",
        action="store_true",
        help_msg="Enable the EMT simulation type.",
    )


def _add_model_argument(
    parser: argparse.ArgumentParser,
    explain: str = "",
    is_required: bool = False,
) -> None:
    """Adds the '--model' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    explain: str
        Additional explanation for the help message.
    is_required: bool
        Whether the argument is required.
    """
    help_msg = "Path to the Dynawo model files (DYD, PAR, INI)."
    if explain:
        help_msg += f" {explain}"
    _add_argument(
        parser,
        "-m",
        "--model",
        arg_type=Path,
        help_msg=help_msg,
        is_required=is_required,
    )


def _add_output_argument(
    parser: argparse.ArgumentParser,
    explain: str = "",
    is_required: bool = False,
) -> None:
    """Adds the '--output' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    explain: str
        Additional explanation for the help message.
    is_required: bool
        Whether the argument is required.
    """
    help_msg = "Path to the output directory."
    if explain:
        help_msg += f" {explain}"
    _add_argument(
        parser,
        "-o",
        "--output",
        arg_type=Path,
        help_msg=help_msg,
        is_required=is_required,
    )


def _add_topology_argument(
    parser: argparse.ArgumentParser,
    explain: str = "",
    is_required: bool = False,
) -> None:
    """Adds the '--topology' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    explain: str
        Additional explanation for the help message.
    is_required: bool
        Whether the argument is required.
    """
    help_msg = "Choice of topology to implement in the DYD file"
    if explain:
        help_msg += f" {explain}"
    _add_argument(
        parser,
        "-t",
        "--topology",
        arg_type=str,
        help_msg=help_msg,
        is_required=is_required,
        choices=["S", "S+i", "S+Aux", "S+Aux+i", "M", "M+i", "M+Aux", "M+Aux+i"],
    )


def _add_curves_argument(
    parser: argparse.ArgumentParser,
    explain: str = "",
    is_required: bool = False,
) -> None:
    """Adds the '--curves' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    explain: str
        Additional explanation for the help message.
    is_required: bool
        Whether the argument is required.
    """
    help_msg = "Path to the directory containing the curves to be used."
    if explain:
        help_msg += f" {explain}"
    _add_argument(
        parser,
        "-c",
        "--curves",
        arg_type=Path,
        help_msg=help_msg,
        is_required=is_required,
    )


def _add_reference_argument(
    parser: argparse.ArgumentParser,
    explain: str = "",
    is_required: bool = False,
) -> None:
    """Adds the 'reference' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    explain: str
        Additional explanation for the help message.
    is_required: bool
        Whether the argument is required.
    """
    help_msg = "Path to the directory containing the reference curves to be used."
    if explain:
        help_msg += f" {explain}"
    _add_argument(
        parser,
        "reference",
        arg_type=Path,
        help_msg=help_msg,
        is_required=is_required,
    )


def _add_validation_argument(
    parser: argparse.ArgumentParser,
    explain: str = "",
    is_required: bool = False,
) -> None:
    """Adds the '--validation' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    explain: str
        Additional explanation for the help message.
    is_required: bool
        Whether the argument is required.
    """
    help_msg = "Choice of process, performance verification (SM, PPM or BESS) "
    help_msg += "vs. RMS model validation (PPM or BESS)"
    if explain:
        help_msg += f" {explain}"
    _add_argument(
        parser,
        "-v",
        "--validation",
        arg_type=str,
        help_msg=help_msg,
        is_required=is_required,
        choices=["performance_SM", "performance_PPM", "model_PPM", "model_BESS"],
    )


def _add_pcs_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--pcs' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-p",
        "--pcs",
        help_msg="Enter one Performance Checking Sheet (PCS) to validate.",
    )


def _add_only_dtr_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--only-dtr' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-od",
        "--only-dtr",
        action="store_true",
        help_msg="Run only the official PCS's defined in the DTR"
        " (i.e., ignore any custom defined PCS).",
    )


def _add_testing_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--testing' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "--testing",
        action="store_true",
        help_msg=argparse.SUPPRESS,  # Suppress help message for testing purposes
    )


def _add_dynamic_model_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--dynamic-model' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-dm",
        "--dynamic-model",
        arg_type=str,
        help_msg="Name of the dynamic model to compile (e.g., 'MyModel.xml')."
        " If not provided, all models will be compiled.",
    )


def _add_force_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--force' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-f",
        "--force",
        action="store_true",
        help_msg="Force recompilation of models, removing existing ones.",
    )


def _add_noisestd_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--noisestd' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-n",
        "--noisestd",
        arg_type=float,
        default=0.0,
        help_msg="Standard deviation of the noise added to the curves, in pu"
        " (recommended range: [0.01, 0.1]).",
    )


def _add_frequency_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--frequency' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-fr",
        "--frequency",
        arg_type=float,
        default=3.0,
        help_msg="Cut-off frequency of the filter used for smoothing the noise,"
        " in Hz (default: 3.0, recommended range: [1.0, 5.0]).",
    )


def _add_results_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--results' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-r",
        "--results",
        arg_type=Path,
        help_msg="Path to a verification results directory. If provided,"
        " 'curves_calculated.csv' and 'dycov.log' files will be copied from here.",
    )


def _add_compression_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the '--compression' argument to the given parser.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        The parser to which the argument will be added.
    """
    _add_argument(
        parser,
        "-comp",
        "--compression",
        arg_type=float,
        default=None,
        help_msg="Relative epsilon for curve simplification using the Visvalingam-Whyatt"
        " algorithm, as a fraction of each signal's range"
        " (e.g. 0.001 = 0.1%). Default: None (no compression).",
    )


def _add_generate_envelopes_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the 'generateEnvelopes' subparser to the given subparsers action.

    Parameters
    ----------
    subparsers: argparse._SubParsersAction
        The subparsers action to which the 'generateEnvelopes' subparser will be added.
    """
    envelops = subparsers.add_parser(
        "generateEnvelopes",
        help="create all the envelopes based on the description of the different test cases",
    )
    _add_debug_argument(envelops)
    _add_ini_argument(envelops, is_required=True)
    _add_emt_argument(envelops)
    _add_output_argument(envelops)
    _add_pcs_argument(envelops)
    _add_only_dtr_argument(envelops)
    dycov_logging.get_logger("CliParsers").debug("Added 'generateEnvelopes' subparser.")


def _add_validate_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the 'validate' subparser to the given subparsers action.

    Parameters
    ----------
    subparsers: argparse._SubParsersAction
        The subparsers action to which the 'validate' subparser will be added.
    """
    validate = subparsers.add_parser(
        "validate",
        help="Validate a Dynawo model against a set of curves.",
    )
    model_or_curves = validate.add_mutually_exclusive_group(required=False)
    _add_debug_argument(validate)
    _add_launcher_argument(validate)
    _add_model_argument(model_or_curves)
    _add_curves_argument(model_or_curves, explain="(when using curves instead of an RMS model)")
    _add_reference_argument(validate, is_required=True)
    _add_output_argument(validate)
    _add_pcs_argument(validate)
    _add_only_dtr_argument(validate)
    _add_testing_argument(validate)
    dycov_logging.get_logger("CliParsers").debug("Added 'validate' subparser.")


def _add_performance_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the 'performance' subparser to the given subparsers action.

    Parameters
    ----------
    subparsers: argparse._SubParsersAction
        The subparsers action to which the 'performance' subparser will be added.
    """
    performance = subparsers.add_parser(
        "performance",
        help="Analyze the performance of a Dynawo model (or its results).",
    )
    _add_debug_argument(performance)
    _add_launcher_argument(performance)
    _add_model_argument(performance)
    _add_curves_argument(
        performance,
        explain="(if a model is also provided, these are used only for graphing)",
    )
    _add_output_argument(performance)
    _add_pcs_argument(performance)
    _add_only_dtr_argument(performance)
    _add_testing_argument(performance)
    dycov_logging.get_logger("CliParsers").debug("Added 'performance' subparser.")


def _add_generate_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the 'generate' subparser to the given subparsers action.

    Parameters
    ----------
    subparsers: argparse._SubParsersAction
        The subparsers action to which the 'generate' subparser will be added.
    """
    generate = subparsers.add_parser(
        "generate",
        help="Create all the necessary input files through a guided process.",
    )
    _add_debug_argument(generate)
    _add_launcher_argument(generate)
    _add_output_argument(generate, is_required=True)
    _add_topology_argument(generate, is_required=True)
    _add_validation_argument(generate, is_required=True)
    dycov_logging.get_logger("CliParsers").debug("Added 'generate' subparser.")


def _add_compile_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the 'compile' subparser to the given subparsers action.

    Parameters
    ----------
    subparsers: argparse._SubParsersAction
        The subparsers action to which the 'compile' subparser will be added.
    """
    compile_model = subparsers.add_parser(
        "compile",
        help="Compile custom Modelica models.",
    )
    _add_debug_argument(compile_model)
    _add_launcher_argument(compile_model)
    _add_dynamic_model_argument(compile_model)
    _add_force_argument(compile_model)
    dycov_logging.get_logger("CliParsers").debug("Added 'compile' subparser.")


def _add_anonymize_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Adds the 'anonymize' subparser to the given subparsers action.

    Parameters
    ----------
    subparsers: argparse._SubParsersAction
        The subparsers action to which the 'anonymize' subparser will be added.
    """
    anonymize = subparsers.add_parser(
        "anonymize",
        help="Generate a new set of curves from a given one, using generic "
        "variable names and with (optional) noise added.",
    )
    _add_debug_argument(anonymize)
    _add_curves_argument(anonymize, is_required=False)
    _add_output_argument(anonymize)
    _add_noisestd_argument(anonymize)
    _add_frequency_argument(anonymize)
    _add_results_argument(anonymize)
    _add_compression_argument(anonymize)
    dycov_logging.get_logger("CliParsers").debug("Added 'anonymize' subparser.")

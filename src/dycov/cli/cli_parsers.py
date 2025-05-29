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


def _add_testing_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the optional --testing argument to the parser."""
    parser.add_argument("--testing", action="store_true", help=argparse.SUPPRESS, default=False)


def _add_launcher_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --dwo_launcher argument to the parser."""
    parser.add_argument(
        "-l",
        "--dwo_launcher",
        required=required,
        help="path to the Dynawo launcher",
        default=None,
    )


def _add_output_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --output_dir argument to the parser."""
    parser.add_argument(
        "-o",
        "--output_dir",
        required=required,
        help="path to the output directory",
        default=None,
    )


def _add_model_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --producer_model argument to the parser."""
    parser.add_argument(
        "-m",
        "--producer_model",
        required=required,
        help="path to the directory containing the producer's RMS model files (DYD, PAR, INI)",
        default=None,
    )


def _add_curves_argument(
    parser: argparse.ArgumentParser, explain: str, required: bool = False
) -> None:
    """Adds the --producer_curves argument to the parser."""
    parser.add_argument(
        "-c",
        "--producer_curves",
        required=required,
        help=f"path to the directory containing producer's curves {explain}",
        default=None,
    )


def _add_verification_results_path(
    parser: argparse.ArgumentParser, required: bool = False
) -> None:
    """Adds the --results_path argument to the parser."""
    parser.add_argument(
        "-r",
        "--results_path",
        required=required,
        help="path to the results directory of a model verification",
        default=None,
    )


def _add_reference_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the --reference_curves argument to the parser."""
    parser.add_argument(
        "reference_curves",
        nargs="?",
        help="path to the directory containing the reference curves used for validation",
        default=None,
    )


def _add_pcs_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --pcs argument to the parser."""
    parser.add_argument(
        "-p",
        "--pcs",
        required=required,
        help="run only the given Performance Checking Sheet (PCS)",
        default=None,
    )


def _add_topology_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --topology argument to the parser."""
    parser.add_argument(
        "-t",
        "--topology",
        required=required,
        help="choice of topology to implement in the DYD file",
        choices=["S", "S+i", "S+Aux", "S+Aux+i", "M", "M+i", "M+Aux", "M+Aux+i"],
        default=None,
    )


def _add_validation_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --validation argument to the parser."""
    parser.add_argument(
        "-v",
        "--validation",
        required=required,
        help="choice of processs, performance verification (SM, PPM or BESS) "
        "vs. RMS model validation (PPM or BESS)",
        choices=["performance_SM", "performance_PPM", "model_PPM", "model_BESS"],
        default=None,
    )


def _add_dynamic_model_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --dynawo_model argument to the parser."""
    parser.add_argument(
        "-m",
        "--dynawo_model",
        required=required,
        help="XML file describing a custom Modelica model",
        default=None,
    )


def _add_force_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --force argument to the parser."""
    parser.add_argument(
        "-f",
        "--force",
        required=required,
        action="store_true",
        help="force the recompilation of all Modelica models (the user's and the tool's own)",
    )


def _add_noise_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --noisestd argument to the parser."""
    parser.add_argument(
        "-n",
        "--noisestd",
        required=required,
        type=float,
        help="standard deviation of the noise added to the curves, in pu (recommended range:"
        " [0.01, 0.1])",
    )


def _add_frequency_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Adds the --frequency argument to the parser."""
    parser.add_argument(
        "-f",
        "--frequency",
        required=required,
        type=float,
        help="cut-off frequency of the filter used for smoothing the noise, in Hz"
        " (default: 3.0, recommended range: [1.0, 5.0])",
        default=3.0,
    )


def _add_debug_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the --debug argument to the parser."""
    parser.add_argument(
        "-d", "--debug", action="store_true", help="show debug messages", default=False
    )


def _add_only_dtr_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the --only_dtr argument to the parser."""
    parser.add_argument(
        "-od",
        "--only_dtr",
        action="store_true",
        help="run only the official PCS's defined in the DTR "
        "(i.e., ignore any custom defined PCS)",
        default=False,
    )


def _add_version_argument(parser: argparse.ArgumentParser) -> None:
    """Adds the --version argument to the parser."""
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
